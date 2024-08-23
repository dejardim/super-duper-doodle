import os
import re
import json
from typing import List
import boto3

from pydantic import BaseModel
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


class Message(BaseModel):
    role: str
    content: str

class Messages(BaseModel):
    messages: List[Message]


@app.post("/project/chat")
def chat():

    response = client.chat.completions.create(
        model='gpt-3.5-turbo-1106',
        temperature=0,
        messages=[
        {"role": "system",  "content": "Você é um Assistente de Suporte para Documentação de Veículos. Seu objetivo é ajudar os clientes a navegar pelos processos de documentação veicular, incluindo registro, renovação de licenças e pagamento de multas. Forneça informações precisas e atualizadas, esclareça dúvidas e oriente os clientes passo a passo através dos procedimentos necessários. Seja acessível, informativo e atento às necessidades individuais de cada cliente."}
        {"role": "user", "content": ""},
        {"role": "assistant", "content": ""},
        ],
        functions=[
            {
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
        "required": ["query"]
    }
}
        ],
        function_call='auto'
    )

    return {"message": "Hello World"}

