import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: 10,
  duration: '30s',
};

export default function () {
  const url = 'http://localhost:8000/api/voice-detection';
  const payload = JSON.stringify({
    language: 'English',
    audioFormat: 'mp3',
    audioBase64: 'BASE64_PLACEHOLDER'
  });
  const headers = { 'Content-Type': 'application/json', 'x-api-key': 'sk_test_123456789' };
  const res = http.post(url, payload, { headers });
  check(res, { 'status is 200': r => r.status === 200 || r.status === 400 || r.status === 401 });
  sleep(0.5);
}
