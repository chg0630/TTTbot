import openai
import streamlit as st
import os, tenacity
import pandas as pd
import numpy as np
from numpy import dot
from numpy.linalg import norm
import ast
from openai.embeddings_utils import get_embedding
from streamlit_chat import message
import requests
import json

# 모든 캐시 데이터 삭제
st.cache_data.clear()  # st.cache를 사용한 경우 st.cache.clear()를 사용하세요

openai.api_key = st.secrets['OPENAI_API_KEY']
api_key = st.secrets["OPENAI_API_KEY"]

MODEL_GPT = "gpt-4o-mini-2024-07-18"

folder_path = './data'
file_name = 'embedding.csv'
file_path = os.path.join(folder_path, file_name)

if os.path.isfile(file_path):
    print(f"{file_path} 파일이 존재합니다.")
    df = pd.read_csv(file_path)
    df['embedding'] = df['embedding'].apply(ast.literal_eval)
else:
    print(f"{file_path} 파일이 존재하지 않아서 임베딩을 시작합니다.")
    folder_path = './data' # data 폴더 경로
    txt_files = [file for file in os.listdir(folder_path) if file.endswith('.txt')]  # txt 파일 목록

    data = []
    for file in txt_files:
        txt_file_path = os.path.join(folder_path, file)
        with open(txt_file_path, 'r', encoding='utf-8') as f:
            text = f.read() # 파일 내용 읽기
            data.append(text)

    df = pd.DataFrame(data, columns=['text'])

    # 데이터프레임의 text 열에 대해서 embedding을 추출
    df['embedding'] = df.apply(lambda row: get_embedding(
        row.text,
        engine="text-embedding-ada-002"
    ), axis=1)
    df.to_csv(file_path, index=False, encoding='utf-8-sig')

def cos_sim(A, B):
  return dot(A, B)/(norm(A)*norm(B))

def return_answer_candidate(df, query):
    query_embedding = get_embedding(
        query,
        engine="text-embedding-ada-002"
    )
    df["similarity"] = df.embedding.apply(lambda x: cos_sim(np.array(x), np.array(query_embedding)))
    top_three_doc = df.sort_values("similarity", ascending=False).head(3)
    return top_three_doc

def create_prompt(df, query):
    result = return_answer_candidate(df, query)
    system_role = f"""You are an artificial intelligence language model named "정채기" that specializes in summarizing \
    and answering documents about Seoul's youth policy, developed by developers 사용자1 and 사용자2.
    You need to take a given document and return a very detailed summary of the document in the query language.
    Here are the document: 
            doc 1 :""" + str(result.iloc[0]['text']) + """
            doc 2 :""" + str(result.iloc[1]['text']) + """
            doc 3 :""" + str(result.iloc[2]['text']) + """
    You must return in Korean. Return a accurate answer based on the document.
    """
    user_content = f"""User question: "{str(query)}". """

    messages = [
        {"role": "system", "content": system_role},
        {"role": "user", "content": user_content}
    ]

    return messages

# GPT에게 질문
def ask_gpt(messages):
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    data = {
        "model": MODEL_GPT,
        "messages": messages,
        "temperature": 0,
        "max_tokens": 1000  # 답변을 1000자 이내로 제한
    }

    response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=data)
    content = json.loads(response.content)
    return content['choices'][0]['message']['content'].strip()

st.image('images/ddc.jpg')

if 'generated' not in st.session_state:
    st.session_state['generated'] = []

if 'past' not in st.session_state:
    st.session_state['past'] = []

with st.form('form', clear_on_submit=True):
    user_input = st.text_input('동두천시의 뉴스에 대해 물어보세요!', '', key='input')
    submitted = st.form_submit_button('Send')

if submitted and user_input:
    # 프롬프트 생성 후 프롬프트를 기반으로 챗봇의 답변을 반환
    messages = create_prompt(df, user_input)
    chatbot_response = ask_gpt(messages)
    st.session_state['past'].append(user_input)
    st.session_state["generated"].append(chatbot_response)

if st.session_state['generated']:
    for i in reversed(range(len(st.session_state['generated']))):
        message(st.session_state['past'][i], is_user=True, key=str(i) + '_user')
        message(st.session_state["generated"][i], key=str(i))
