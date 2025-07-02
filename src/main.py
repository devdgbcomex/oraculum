from fastapi import FastAPI
from database import get_connection
from typing import List
import json
from fastapi.responses import StreamingResponse
import pyodbc
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from io import BytesIO

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

@app.get("/sugestao-rolos/{pedido}")
def sugestao_rolos(pedido: str):
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Executa a procedure com o parâmetro
        cursor.execute("EXEC uspEnderecamentoParaAtenderPedidoGeral ?", pedido)

        # Monta resultado em JSON
        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/pdf/sugestao-rolos/{pedido}")
def gerar_pdf_stream(pedido: str):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("EXEC uspEnderecamentoParaAtenderPedidoGeral ?", pedido)
        rows = cursor.fetchall()
        col_names = [desc[0] for desc in cursor.description]

        if not rows:
            return JSONResponse(status_code=404, content={"erro": "Nenhum item encontrado"})

        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=landscape(A4))  # Agora em paisagem
        width, height = landscape(A4)
        x_margin = 40
        y = height - 40

        c.setFont("Helvetica-Bold", 14)
        c.drawString(x_margin, y, f"Sugestão de Rolos - Pedido {pedido}")
        y -= 30

        c.setFont("Helvetica-Bold", 10)
        header = " | ".join(col_names)
        lines = quebra_linha(header, width - 2 * x_margin)
        for line in lines:
            c.drawString(x_margin, y, line)
            y -= 14
        y -= 10

        c.setFont("Helvetica", 9)
        for row in rows:
            linha = " | ".join(str(val) for val in row)
            for l in quebra_linha(linha, width - 2 * x_margin):
                c.drawString(x_margin, y, l)
                y -= 12
                if y < 40:
                    c.showPage()
                    y = height - 40
                    c.setFont("Helvetica", 9)

        c.save()
        buffer.seek(0)

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"inline; filename=sugestao_{pedido}.pdf"}
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"erro": "Erro ao gerar PDF", "detalhes": str(e)}
        )


def quebra_linha(texto, largura_maxima, tamanho_medio_char=5):
    """Divide uma string em múltiplas linhas com base na largura máxima estimada."""
    max_chars = int(largura_maxima / tamanho_medio_char)
    palavras = texto.split(" ")
    linhas = []
    linha = ""
    for palavra in palavras:
        if len(linha + " " + palavra) <= max_chars:
            linha += " " + palavra if linha else palavra
        else:
            linhas.append(linha)
            linha = palavra
    if linha:
        linhas.append(linha)
    return linhas