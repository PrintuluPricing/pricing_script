from dotenv import load_dotenv
import psycopg2
import pandas as pd
import io
import os
import numpy as np

load_dotenv()

SQL_URL = os.environ.get('SQL_URL')


def connect_database():
    return psycopg2.connect(SQL_URL)


connection = connect_database()
cursor = connection.cursor()


def get_sql_table(table_name:str):
    with connection.cursor() as cur:
        """Reads SQL Table"""
        read_all_query = f"""
        SELECT * from {table_name};
        """
        cur.execute(read_all_query)
        data = cur.fetchall()
    return data


def get_table_column(table_name:str, column:str):
    with connection.cursor() as cur:
        """Reads SQL Table"""
        read_all_query = f"""
        SELECT {column} from {table_name};
        """
        cur.execute(read_all_query)
        data = cur.fetchall()
    data = [item[0] for item in data]
    return data


def get_sql_columns(table_name:str):
    with connection.cursor() as cur:
        """Reads SQL Table columns"""
        read_all_query = f"""
        SELECT column_name FROM information_schema.columns WHERE table_name = '{table_name}';
        """
        cur.execute(read_all_query)
        data = cur.fetchall()
        data = [item[0] for item in data]
    return data


def insert_dataframe_to_postgres(df, table_name, identifier=None):
    # TODO: Based on identifier exclude duplicates

    if identifier != None:
        pass

    buff = io.StringIO()
    sql_columns = get_sql_columns(table_name)
    df.columns = [col.replace(" ", "_").lower() for col in df.columns]
    df = df[[col for col in df.columns if col in sql_columns]]
    for col in df.columns:
        if df[col].dtype != object:
            df[col] = df[col].fillna(0)


    df.to_csv(buff, index=False, sep="|", header=False)
    cols = tuple(df.columns)
    buff.seek(0)

    with connection.cursor() as cur:
        cur.copy_from(buff, table_name, sep="|", columns=cols)
        print("copying done")
    connection.commit()


if __name__ == "__main__":
    pis = get_table_column("pi_based", "position_id")
    print(pis)
