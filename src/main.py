import os
import re
import json
from typing import List
import boto3

from openai import OpenAI
from pydantic import BaseModel, field_validator
from unidecode import unidecode
from fastapi.responses import JSONResponse
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, status
from mangum import Mangum
from io import BytesIO
# from embedchain import App


app = FastAPI()
handler = Mangum(app, lifespan="off")

session = boto3.session.Session(
    region_name='us-east-1',
    aws_access_key_id='',
    aws_secret_access_key='',
)

s3_client = session.client('s3')

def sanitize_filename(filename):
    unidecoded = unidecode(filename)
    # Remove caracteres não alfanuméricos (exceto pontos e underlines) e substitui espaços por underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_.]', '', unidecoded.replace(' ', '_'))
    return sanitized


@app.post("/file/upload")
async def upload_file(file: UploadFile = File(...), owner: str = Form(...)):
    # Verificação do tipo de arquivo
    if not file.filename.endswith(('.csv', '.pdf')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only CSV and PDF files are allowed."
        )

    # Leitura do conteúdo do arquivo
    contents = await file.read()
    file_size = len(contents)

    # Retorna o ponteiro do arquivo para o início
    await file.seek(0)

    # Verificação do tamanho do arquivo
    if file_size > 2 * 1024 * 1024:  # 2 MB em bytes
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="The file size exceeds the maximum limit of 2 MB."
        )

    sanitized_filename = sanitize_filename(file.filename)
    bucket_name = "alive-platform-test-upload"
    s3_file_name = f"{owner}/{sanitized_filename}"

    # Faz upload do arquivo para o S3
    try:
        buffer = BytesIO(contents)
        # Primeiro, tenta fazer o HEAD do objeto para verificar se ele já existe
        try:
            s3_client.head_object(Bucket=bucket_name, Key=s3_file_name)
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A file with the same name already exists in the bucket."
            )
        except s3_client.exceptions.ClientError as e:
            # Se o arquivo não existir, continua com o upload
            s3_client.upload_fileobj(buffer, bucket_name, s3_file_name)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file to S3: {str(e)}"
        )

    # Prepara e faz upload do arquivo de metadados
    metadata = {
        "metadataAttributes": {
            "owner": owner,
        }
    }
    metadata_buffer = BytesIO(json.dumps(metadata, indent=4).encode('utf-8'))
    try:
        s3_client.upload_fileobj(metadata_buffer, bucket_name, f'{s3_file_name}.metadata.json')
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload metadata to S3: {str(e)}"
        )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": f"File and metadata uploaded successfully."}
    )


class Message(BaseModel):
    role: str
    content: str

class Messages(BaseModel):
    messages: List[Message]

    @field_validator('messages')
    def check_max_messages(cls, v):
        max_messages = 5  # Definir o limite máximo de mensagens
        if len(v) > max_messages:
            raise ValueError(f'Máximo de {max_messages} mensagens permitidas')
        return v


@app.post("/project/chat")
def chat(body: Messages):
    client = OpenAI(api_key='')

    response = client.chat.completions.create(
        model='gpt-3.5-turbo-0125',
        temperature=0,
        messages=[
            {"role": "system",  "content": "Você é um Assistente de Suporte para Documentação de Veículos. Seu objetivo é ajudar os clientes a navegar pelos processos de documentação veicular, incluindo registro, renovação de licenças e pagamento de multas. Forneça informações precisas e atualizadas, esclareça dúvidas e oriente os clientes passo a passo através dos procedimentos necessários. Seja acessível, informativo e atento às necessidades individuais de cada cliente."},
            *body.messages
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "consultar_informacao",
                    "description": "Consulta informações na base de conhecimento do projeto quando identifica a necessidade de obter contexto adicional para responder adequadamente ao usuário.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Define a consulta específica ou a informação que o modelo precisa verificar dentro da base de conhecimento."
                            }
                        },
                    },
                    "required": ["query"]
                }
            }
        ]
    )

    if not response.choices[0].message.tool_calls:
        return response.choices[0].message.content

    # os.environ["OPENAI_API_KEY"] = ""


    # arguments = json.loads(response.choices[0].message.tool_calls[0].function.arguments)

    client = boto3.client('bedrock-agent-runtime')

    response = client.retrieve(
        knowledgeBaseId="",
        retrievalQuery={
            'text': "pizzaplanet",
        },
        retrievalConfiguration={
            'vectorSearchConfiguration': {
                'numberOfResults': 1,
                'overrideSearchType': 'SEMANTIC',
                'filter': {
                    "equals": {
                        'key': 'owner',
                        'value': 'teste'
                    }
                }
            }
        }
    )

    return response
