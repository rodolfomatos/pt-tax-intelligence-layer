// Ficheiro: test_final_debug.mjs
// Objetivo: Teste robusto com correção de 'duplex' e URL para evitar hanging.

import { performance } from 'perf_hooks';

// 1. Correção do URL (Removida a dupla barra // antes de api)
const ENDPOINT = "https://api.iaedu.pt/agent-chat/api/v1/agent/cmamvd3n40000c801qeacoad2/stream";
const API_KEY = process.env.IAEDU_API_KEY || "sk-usr-hlwl7kkgz8byfkzl3sb6umf33kw4rnx3e1o"; 
const CHANNEL_ID = "cmh0rfgmn0i64j801uuoletwy";

async function testRobustRequest() {
    console.log("--- A iniciar teste ROBUSTO ---");

    const formData = new FormData();
    formData.append("channel_id", CHANNEL_ID);
    formData.append("thread_id", `test-debug-${Date.now()}`); 
    formData.append("user_info", "{}");
    formData.append("message", "Isto é um teste de conectividade.");

    // Controlador de Timeout (para não ficares pendurado para sempre)
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 segundos timeout máximo

    const start = performance.now();

    try {
        console.log(`URL: ${ENDPOINT}`);
        console.log("A enviar pedido...");

        const response = await fetch(ENDPOINT, {
            method: "POST",
            headers: {
                'x-api-key': API_KEY,
                // NOTA: Não definimos Content-Type, o fetch gera-o com o boundary correto.
                // Forçamos o fecho da conexão para evitar hanging de keep-alive
                'Connection': 'close' 
            },
            body: formData,
            
            // CRÍTICO PARA NODE.JS:
            // Define o modo duplex para streams. Resolve problemas de hanging em POSTs.
            duplex: 'half', 
            
            signal: controller.signal
        });

        clearTimeout(timeoutId); // Limpar timeout se respondeu

        const duration = (performance.now() - start) / 1000;
        console.log(`\nResposta recebida em ${duration.toFixed(2)}s`);
        console.log(`Status: ${response.status} ${response.statusText}`);

        if (!response.ok) {
            const text = await response.text();
            console.error("ERRO CORPO:", text);
            return;
        }

        // Leitura do Stream
        console.log("--- A ler Stream ---");
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let chunkCount = 0;

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            chunkCount++;
            const chunk = decoder.decode(value, { stream: true });
            
            // Mostrar apenas o início para confirmar que chegam dados
            if (chunkCount === 1) {
                console.log("Primeiros dados recebidos:");
                console.log(chunk.substring(0, 100) + "...");
            }
        }
        console.log("\nStream concluído com sucesso.");

    } catch (error) {
        if (error.name === 'AbortError') {
            console.error("\nERRO: Timeout! O servidor não respondeu em 10 segundos.");
        } else {
            console.error("\nERRO DE EXECUÇÃO:", error);
        }
    } finally {
        clearTimeout(timeoutId);
    }
}

testRobustRequest();
