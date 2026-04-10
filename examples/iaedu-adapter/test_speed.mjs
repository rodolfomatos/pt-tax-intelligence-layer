// Ficheiro: test_speed.mjs
// Objetivo: Medir a velocidade real de geração de tokens (TPS) da API.

import { performance } from 'perf_hooks';

// CONFIGURAÇÃO
const ENDPOINT = "https://api.iaedu.pt/agent-chat//api/v1/agent/cmamvd3n40000c801qeacoad2/stream";
const API_KEY = process.env.IAEDU_API_KEY; 
const CHANNEL_ID = "cmh0rfgmn0i64j801uuoletwy";

if (!API_KEY) {
    console.error("ERRO: Define a variável de ambiente IAEDU_API_KEY antes de correr.");
    process.exit(1);
}

async function testSpeed() {
    const threadId = `speed-test-${Date.now()}`;
    // Um prompt que obrigue a gerar texto longo para podermos medir a velocidade
    const message = "Escreve um poema longo sobre a importância da velocidade na computação.";

    const formData = new FormData();
    formData.append("channel_id", CHANNEL_ID);
    formData.append("thread_id", threadId);
    formData.append("user_info", "{}");
    formData.append("message", message);

    console.log("--- A INICIAR TESTE DE VELOCIDADE ---");
    console.log("A pedir geração longa...");

    const startTotal = performance.now();
    let firstTokenTime = 0;
    let tokenCount = 0;

    try {
        const response = await fetch(ENDPOINT, {
            method: "POST",
            headers: { 'x-api-key': API_KEY },
            body: formData,
        });

        if (!response.ok) throw new Error(`Erro API: ${response.status}`);

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            if (firstTokenTime === 0) {
                firstTokenTime = performance.now();
                console.log(`Tempo até ao primeiro token (Latência): ${((firstTokenTime - startTotal)/1000).toFixed(2)}s`);
            }

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop(); // Guarda o resto incompleto

            for (const line of lines) {
                if (!line) continue;
                try {
                    const json = JSON.parse(line);
                    if (json.type === "token" && json.content) {
                        tokenCount++;
                        process.stdout.write("."); // Feedback visual
                    }
                } catch (e) {}
            }
        }

        const endTotal = performance.now();
        const generationTime = (endTotal - firstTokenTime) / 1000;
        const tps = tokenCount / generationTime;

        console.log("\n\n--- RESULTADOS ---");
        console.log(`Total Tokens: ${tokenCount}`);
        console.log(`Tempo de Geração: ${generationTime.toFixed(2)}s`);
        console.log(`VELOCIDADE: ${tps.toFixed(2)} tokens/segundo`);
        
        if (tps < 5) console.warn("AVISO: A API de origem é MUITO LENTA. O adaptador não pode fazer milagres.");
        else console.log("NOTA: A velocidade da API é aceitável.");

    } catch (error) {
        console.error(error);
    }
}

testSpeed();
