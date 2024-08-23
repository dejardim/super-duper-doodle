import os
import re
import json
import boto3

from unidecode import unidecode
from fastapi.responses import JSONResponse
from fastapi import FastAPI, File, UploadFile, Form, HTTPException, status
from mangum import Mangum
from io import BytesIO


app = FastAPI()
handler = Mangum(app, lifespan="off")

session = boto3.session.Session(
    aws_access_key_id='',
    aws_secret_access_key='',
    region_name='us-east-1'
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
