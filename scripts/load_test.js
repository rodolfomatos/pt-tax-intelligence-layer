import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

export let options = {
    stages: [
        { duration: '30s', target: 10 },  // ramp up to 10 users
        { duration: '1m', target: 10 },   // stay at 10 users
        { duration: '30s', target: 50 },  // ramp up to 50 users
        { duration: '1m', target: 50 },   // stay at 50
        { duration: '30s', target: 100 }, // ramp up to 100
        { duration: '1m', target: 100 },  // peak
        { duration: '30s', target: 0 },   // ramp down
    ],
    thresholds: {
        http_req_duration: ['p(95)<500'], // 95% of requests < 500ms
        http_errors: ['rate<0.01'],        // error rate < 1%
    },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_KEY = __ENV.API_KEY || 'test-api-key';

const headers = {
    'X-API-Key': API_KEY,
    'Content-Type': 'application/json',
};

const sampleRequest = {
    operation_type: 'expense',
    description: 'Material de escritório',
    amount: 50.00,
    currency: 'EUR',
    entity_type: 'department',
    context: {
        project_type: 'internal',
        activity_type: 'taxable',
        location: 'PT',
    },
};

export default function () {
    // Test health endpoint
    let res = http.get(`${BASE_URL}/health`);
    check(res, { 'health 200': (r) => r.status === 200 });

    // Test analyze endpoint
    res = http.post(`${BASE_URL}/tax/analyze`, JSON.stringify(sampleRequest), { headers });
    check(res, {
        'analyze 200': (r) => r.status === 200,
        'has decision': (r) => r.json('decision') !== undefined,
        'has confidence': (r) => r.json('confidence') !== undefined,
    });

    // Test search endpoint
    res = http.get(`${BASE_URL}/tax/search?q=iva&limit=5`, { headers: { ...headers, 'X-API-Key': API_KEY } });
    check(res, {
        'search 200': (r) => r.status === 200,
        'has results': (r) => r.json('count') !== undefined,
    });

    sleep(1);
}
