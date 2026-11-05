from fii_analyzer.db.model import FiiBalancoMensal, FiiMetricaMensal, FiiFundoMensal
from fii_analyzer.db.insert import insert_data_in_database

def insert_data(file_name, file_data, year):

    if file_name == f"inf_mensal_fii_ativo_passivo_{year}.csv":
        insert_data_in_database(FiiBalancoMensal, file_data)

    if file_name == f"inf_mensal_fii_complemento_{year}.csv":
        insert_data_in_database(FiiMetricaMensal, file_data)

    if file_name == f"inf_mensal_fii_geral_{year}.csv":
        insert_data_in_database(FiiFundoMensal, file_data)