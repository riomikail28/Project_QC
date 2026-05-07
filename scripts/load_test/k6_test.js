import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '1m', target: 50 },
    { duration: '3m', target: 100 },
    { duration: '2m', target: 0 },
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    'http_req_failed': ['rate<0.01'],
  },
};

const BASE = __ENV.STAGING_URL || 'http://localhost:5000';

export default function () {
  const res = http.get(`${BASE}/api/qc/health`);
  check(res, {
    'status is 200': (r) => r.status === 200,
  });
  sleep(1);
}
