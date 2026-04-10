// Ficheiro: test_latency.mjs
// Objetivo: Medir o tempo de resposta (TTFB) da API para validar timeouts.

import { performance } from 'perf_hooks';

const ENDPOINT = "https://api.iaedu.pt/agent-chat//api/v1/agent/cmamvd3n40000c801qeacoad2/stream";
const API_KEY = process.env.IAEDU_API_KEY || "A_TUA_CHAVE_AQUI_SE_NAO_ESTIVER_NO_ENV"; 
// Nota: Garante que exportas a chave no terminal antes de correr, ou cola-a acima.

const CHANNEL_ID = "cmh0rfgmn0i64j801uuoletwy";

// Função auxiliar para enviar pedido
async function sendRequest(testName, message, threadId) {
    console.log(`\n--- A iniciar teste: ${testName} ---`);
    console.log(`Thread ID: ${threadId}`);
    
    const formData = new FormData();
    formData.append("channel_id", CHANNEL_ID);
    formData.append("thread_id", threadId);
    formData.append("user_info", "{}");
    formData.append("message", message);

    const start = performance.now();

    try {
        const response = await fetch(ENDPOINT, {
            method: "POST",
            headers: { 'x-api-key': API_KEY },
            body: formData,
        });

        const ttfb = performance.now() - start;
        console.log(`Status: ${response.status}`);
        
        if (!response.ok) {
            const text = await response.text();
            console.error(`ERRO: ${text}`);
            return;
        }

        console.log(`Tempo até ao primeiro byte (TTFB): ${(ttfb / 1000).toFixed(2)} segundos`);

        // Ler apenas o início para confirmar funcionamento
        const reader = response.body.getReader();
        const { value } = await reader.read();
        const decoder = new TextDecoder();
        console.log("Primeiro chunk recebido:", decoder.decode(value).substring(0, 50) + "...");
        
        // Cancelar para poupar recursos
        reader.cancel(); 
        console.log("Stream encerrado com sucesso.");

    } catch (error) {
        console.error("Erro de rede/fetch:", error);
    }
}

async function runTests() {
    // Teste 1: Mensagem simples (deve ser rápido)
    // Usamos um ID aleatório para não carregar histórico antigo
    const randomId = `test-${Date.now()}`;
    await sendRequest("Ping Simples", "Olá, isto é um teste de latência.", randomId);

    // Teste 2: Mensagem um pouco maior (simulação básica)
    const longMessage = "Explica detalhadamente a teoria da relatividade geral e como ela se compara com a mecânica quântica, fornecendo exemplos históricos.";
    await sendRequest("Carga Média", longMessage, randomId);
}

runTests();
