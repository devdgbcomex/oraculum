from fastapi import FastAPI
from database import get_connection
from typing import List
import json

app = FastAPI()

@app.get("/dados", summary="Consulta CTE_Peca + joins")
def get_dados():
    conn = get_connection()
    cursor = conn.cursor()

    query = """
    SELECT
        CP.Lote_Interno, 
        CP.Aviso,
        CP.Gaveta,
        CP.SubLote,
        CP.Situacao,
        CP.Nro_Rolo,
        CP.Nro_Peca,
        CP.Produto,
        CP.Categoria,
        CP.Categoria_Tinto,
        CP.Cor,
        CP.Desenho,
        CP.Variante,
        CP.Largura,
        FORMAT(CP.Metros, 'N4', 'pt-BR') AS Metros,
        FORMAT(CP.Peso, 'N4', 'pt-BR') AS Peso,
        CP.Tear AS Rolo_Packlist, 
        CP.Data_Entrada,
        (CP.Nro_Rolo + CP.Situacao + CP.Cor + CP.Desenho) AS Chave, 
        PT.Linha
    FROM DBMicrodata_DGB.dbo.Cte_Peca CP 
    LEFT JOIN DBMicrodata_DGB.dbo.CTE_Baixa CB 
        ON (CP.Empresa = CB.Empresa 
            AND CP.Situacao = CB.Situacao 
            AND CP.Nro_Rolo = CB.Nro_Rolo 
            AND CP.Nro_Peca = CB.Nro_Peca) 
    LEFT JOIN DBMicrodata_DGB.dbo.Produtos_Tecidos PT 
        ON (CP.EmpProd = PT.Empresa 
            AND CP.Produto = PT.Produto) 
    WHERE CP.Nro_Rolo_Origem IS NULL 
        AND CB.Empresa IS NULL 
    ORDER BY
        CP.SubLote ASC,
        CP.Tear ASC,
        CP.Gaveta ASC,
        CP.Produto ASC,
        CP.Cor ASC,
        CP.Aviso DESC,		
        CP.Nro_Rolo DESC,		
        CP.Categoria_Tinto ASC
    """

    cursor.execute(query)
    columns = [col[0] for col in cursor.description]
    results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    return results
