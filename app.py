import asyncio
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from playwright.async_api import async_playwright

app = Flask(__name__)

# --- ROBÔ DA SMILES (FILTRADO POR DATA E CABINE) ---
async def pesquisar_na_smiles(origem, destino, data_str):
    async with async_playwright() as p:
        iphone = p.devices['iPhone 13']
        browser = await p.chromium.launch(headless=True,
    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
        context = await browser.new_context(**iphone)
        page = await context.new_page()
        
        resultados_dia = []
        
        # Testamos as duas cabines (ECONOMIC e BUSINESS)
        for cabine in ['ECONOMIC', 'BUSINESS']:
            url = f"https://www.smiles.com.br/m/voos?originAirport={origem}&destinationAirport={destino}&departureDate={data_str}&adults=1&infants=0&children=0&cabin={cabine}&isOneWay=true"
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_selector('.flight-list-item, .card-flight', timeout=10000)
                
                voos = await page.evaluate(f'''() => {{
                    let resultados = [];
                    let cartoes = document.querySelectorAll('.flight-list-item, .card-flight');
                    cartoes.forEach(c => {{
                        let cia = c.querySelector('.airline-name')?.innerText || 'Parceira';
                        let precoTexto = c.querySelector('.miles-price, .price-value')?.innerText || 'N/A';
                        let milhasValor = parseInt(precoTexto.replace(/[^0-9]/g, '')) || 0;
                        
                        // FILTRO AWARD: Ignora voos operados pela própria GOL
                        if (cia.toUpperCase() !== 'GOL' && milhasValor > 0) {{
                            resultados.push({{ 
                                programa: 'Smiles (Award)', 
                                companhia: cia, 
                                milhas: milhasValor,
                                cabine: "{'Econômica' if cabine == 'ECONOMIC' else 'Executiva'}",
                                data: "{data_str}"
                            }});
                        }}
                    }});
                    return resultados;
                }}''')
                resultados_dia.extend(voos)
            except:
                pass
                
        await browser.close()
        return resultados_dia

# --- ROBÔ DA AZUL (INTERLINE AWARD ECONOMICA E EXECUTIVA) ---
async def pesquisar_na_azul(origem, destino, data_str):
    async with async_playwright() as p:
        iphone = p.devices['iPhone 13']
        browser = await p.chromium.launch(headless=True,
    args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
        context = await browser.new_context(**iphone)
        page = await context.new_page()
        
        resultados_dia = []
        
        # Testamos as duas cabines (ECONOMY e BUSINESS)
        for cabine in ['ECONOMY', 'BUSINESS']:
            url = f"https://interline.voeazul.com.br/m/voos?originAirport={origem}&destinationAirport={destino}&departureDate={data_str}&adults=1&cabin={cabine}&isOneWay=true"
            try:
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_selector('.flight-card, .card-voo-azul, .flight-list-item', timeout=10000)
                
                voos = await page.evaluate(f'''() => {{
                    let resultados = [];
                    let cartoes = document.querySelectorAll('.flight-card, .card-voo-azul, .flight-list-item');
                    cartoes.forEach(c => {{
                        let cia = c.querySelector('.airline-name, .airline-logo img')?.alt || c.querySelector('.airline-name')?.innerText || 'Parceira';
                        let precoTexto = c.querySelector('.points-price, .preco-pontos, .miles-price')?.innerText || 'N/A';
                        let milhasValor = parseInt(precoTexto.replace(/[^0-9]/g, '')) || 0;
                        
                        if (cia.toUpperCase() !== 'AZUL' && milhasValor > 0) {{
                            resultados.push({{ 
                                programa: 'Azul Interline', 
                                companhia: cia, 
                                milhas: milhasValor,
                                cabine: "{'Econômica' if cabine == 'ECONOMY' else 'Executiva'}",
                                data: "{data_str}"
                            }});
                        }}
                    }});
                    return resultados;
                }}''')
                resultados_dia.extend(voos)
            except:
                pass
                
        await browser.close()
        return resultados_dia

# --- TELA DO SITE ---
@app.route('/')
def home():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Radar de Vagas Award Completo</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 700px; margin: 40px auto; padding: 20px; box-shadow: 0 0 10px rgba(0,0,0,0.1); border-radius: 8px; }
            input, select, button { width: 100%; padding: 10px; margin: 10px 0; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
            button { background-color: #1a4f8a; color: white; border: none; cursor: pointer; font-size: 16px; font-weight: bold; }
            .checkbox-group { margin: 15px 0; display: flex; gap: 20px; }
            #resultados { margin-top: 20px; font-weight: bold; }
            .voo-item { background: #f4f4f4; padding: 12px; margin: 8px 0; border-left: 5px solid #1a4f8a; display: flex; justify-content: space-between; align-items: center; }
            .badge { background: #333; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
            .date-badge { background: #008CBA; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; margin-right: 5px; }
            .cabine-badge { background: #28a745; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; margin-right: 5px; }
            .cabine-exec { background: #6f42c1; }
        </style>
    </head>
    <body>
        <h2>Radar Award Multi-Datas (Econômica & Executiva)</h2>
        <input type="text" id="origem" placeholder="Origem" value="CPT">
        <input type="text" id="destino" placeholder="Destino" value="GRU">
        
        <label>A partir do dia:</label>
        <input type="date" id="data_inicio">
        
        <label>Quantidade de dias para buscar em lote:</label>
        <select id="qtd_dias">
            <option value="3">Buscar 3 dias seguidos</option>
            <option value="5" selected>Buscar 5 dias seguidos</option>
            <option value="7">Buscar 7 dias seguidos</option>
        </select>
        
        <div class="checkbox-group">
            <label><input type="checkbox" id="chkSmiles" checked> Smiles Award</label>
            <label><input type="checkbox" id="chkAzul" checked> Azul Interline</label>
        </div>
        
        <button onclick="buscarLoteVoos()">Varrer Calendário</button>
        
        <div id="resultados"></div>

        <script>
            async function buscarLoteVoos() {
                const divRes = document.getElementById('resultados');
                divRes.innerHTML = "Varrendo as cabines Econômica e Executiva dia a dia... Como a busca duplicou, o processo pode levar cerca de 1 a 2 minutos.";
                
                const orig = document.getElementById('origem').value;
                const dest = document.getElementById('destino').value;
                const dtInicio = document.getElementById('data_inicio').value;
                const qtdDias = document.getElementById('qtd_dias').value;
                const smiles = document.getElementById('chkSmiles').checked;
                const azul = document.getElementById('chkAzul').checked;

                if (!dtInicio) {
                    divRes.innerHTML = "<span style='color:red;'>Por favor, selecione a data de início!</span>";
                    return;
                }

                const response = await fetch(`/buscar_lote?origem=${orig}&destino=${dest}&data_inicio=${dtInicio}&qtd_dias=${qtdDias}&smiles=${smiles}&azul=${azul}`);
                const todosVoos = await response.json();

                if(todosVoos.length === 0) {
                    divRes.innerHTML = "Nenhuma vaga Award localizada no período informado.";
                    return;
                }

                divRes.innerHTML = `<h3>Vagas Encontradas (Ordenado por Menor Preço):</h3>`;
                todosVoos.forEach(v => {
                    const partesData = v.data.split('-');
                    const dataFormatada = `${partesData[2]}/${partesData[1]}/${partesData[0]}`;
                    
                    const classeCabine = v.cabine === 'Executiva' ? 'cabine-badge cabine-exec' : 'cabine-badge';
                    
                    divRes.innerHTML += `
                        <div class="voo-item">
                            <span>
                                <span class="date-badge">${dataFormatada}</span>
                                <span class="${classeCabine}">${v.cabine}</span>
                                <strong>${v.companhia}</strong> | ${parseInt(v.milhas).toLocaleString('pt-BR')} pontos
                            </span>
                            <span class="badge">${v.programa}</span>
                        </div>`;
                });
            }
        </script>
    </body>
    </html>
    '''

@app.route('/buscar_lote')
def buscar_lote():
    origem = request.args.get('origem')
    destino = request.args.get('destino')
    data_inicio_str = request.args.get('data_inicio')
    qtd_dias = int(request.args.get('qtd_dias', 20))
    
    quer_smiles = request.args.get('smiles') == 'true'
    quer_azul = request.args.get('azul') == 'true'
    
    data_inicio = datetime.strptime(data_inicio_str, '%Y-%m-%d')
    lista_final = []
    
    for i in range(qtd_dias):
        data_atual = data_inicio + timedelta(days=i)
        data_atual_str = data_atual.strftime('%Y-%m-%d')
        
        if quer_smiles:
            lista_final.extend(asyncio.run(pesquisar_na_smiles(origem, destino, data_atual_str)))
            
        if quer_azul:
            lista_final.extend(asyncio.run(pesquisar_na_azul(origem, destino, data_atual_str)))
            
    lista_final = sorted(lista_final, key=lambda k: int(k['milhas']))
    return jsonify(lista_final)

if __name__ == '__main__':
    app.run(debug=True)
