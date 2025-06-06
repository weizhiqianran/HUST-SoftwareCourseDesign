# -*- coding: utf-8 -*-
# @Time    : 2024/12/27 16:01
# @Author  : Junzhe Yi
# @File    : ask_questions_v2.py
# @Software: PyCharm

import timeit
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Milvus
from libs.read_config import ReadConfig
from langchain.chains import RetrievalQA
from libs import qa_template
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate


def set_qa_prompt():
    prompt = PromptTemplate(template=qa_template,
                            input_variables=['context', 'question'])
    return prompt


def build_retrieval_qa(_llm, prompt, _retriever):

    db_qa = RetrievalQA.from_chain_type(llm=_llm,
                                        chain_type='stuff',
                                        retriever=_retriever,
                                        return_source_documents=True,
                                        verbose=True,
                                        chain_type_kwargs={'prompt': prompt})
    return db_qa


def ask_question_openai(query_text):
    my_config = ReadConfig("config/config.ini")
    top_k = int(my_config.search_top_k)
    search_parameters = {
        "metric_type": "COSINE",
        "offset": 0,
        "ignore_growing": False,
        "params": {"ef": 32}
    }
    model_name = my_config.SentenceTransformer_model
    embeddings = HuggingFaceEmbeddings(model_name=model_name)
    connection_args = {"host": my_config.host,
                       "port": int(my_config.port),
                       "user": my_config.user,
                       "password": None
                       }
    vector_db: Milvus = Milvus(
        embedding_function=embeddings,
        collection_name="PythonBooks",
        search_params=search_parameters,
        connection_args=connection_args,
        text_field="book_chunk",
        vector_field="book_chunk_vec",
        consistency_level="Session"
    )
    retriever = vector_db.as_retriever(search_kwargs={'k': top_k,
                                                      "additional": ["certainty"],
                                                      "score_threshold": 0.9
                                                      },
                                       search_type="similarity"
                                       )
    qa_prompt = set_qa_prompt()
    openai_llm = ChatOpenAI(model_name="gpt-3.5-turbo",
                            temperature=0,
                            openai_api_key=my_config.openai_api_key
                            )
    dbqa = build_retrieval_qa(openai_llm, qa_prompt, retriever)
    llm_response = dbqa.invoke(query_text)
    return llm_response


if __name__ == '__main__':
    query = input("Please enter the question: ")
    start_time = timeit.default_timer()
    response = ask_question_openai(query)


    print(f'\n\033[92m Answer: \033[0;0m {response["result"]}')
    print("\033[38;5;208m*******************************\033[0;0m")
    source_docs = response['source_documents']
    for i, doc in enumerate(source_docs):
        print(f'\nSource Document {i + 1}\n')
        print(f'Source Text: {doc.page_content}')
        print("\033[38;5;208m*******************************\033[0;0m")
    print('=' * 50)
    end_time = timeit.default_timer()
    total_time = (end_time - start_time) / 60
    print("Time to retrieve response %.2f(minute(s)):" % total_time)
