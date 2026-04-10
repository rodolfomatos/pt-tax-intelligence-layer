// Ficheiro: test_api_dynamic_thread.mjs
// (Baseado no nosso primeiro teste)

async function testIAEduAPI() {
    const endpoint = "https://api.iaedu.pt/agent-chat//api/v1/agent/cmamvd3n40000c801qeacoad2/stream";
    const apiKey = "sk-usr-hlwl7kkgz8byfkzl3sb6umf33kw4rnx3e1o";

    // --- A ALTERAÇÃO ESTÁ AQUI ---
    // Em vez do ID antigo, vamos inventar um novo ID de thread.
    const dynamicThreadId = "thread-openwebui-teste-123456789";
    // -----------------------------

    const formData = new FormData();
    formData.append("channel_id", "cmh0rfgmn0i64j801uuoletwy");
    formData.append("thread_id", dynamicThreadId); // Usar o novo ID
    formData.append("user_info", "{}");
    formData.append("message", "Qual é o valor de X?");

    console.log(`A testar com um Thread ID dinâmico: ${dynamicThreadId}`);
    console.log("--- INÍCIO DO STREAM ---");

    try {
        const response = await fetch(endpoint, {
            method: "POST",
            headers: { 'x-api-key': apiKey },
            body: formData,
        });

        if (!response.ok) {
            console.error(`\nErro na API: ${response.status} ${response.statusText}`);
            const errorBody = await response.text();
            console.error("Corpo do erro:", errorBody);
            return;
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            // Vamos apenas mostrar o output, não precisamos de o interpretar
            process.stdout.write(decoder.decode(value, { stream: true }));
        }

    } catch (error) {
        console.error("\nErro de rede:", error);
    } finally {
        console.log("\n--- FIM DO STREAM ---");
    }
}

testIAEduAPI();
