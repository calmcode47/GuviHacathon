$ErrorActionPreference = "Stop"
$url = "http://localhost:8000"
$apiKey = $env:API_KEY
if (-not $apiKey) { $apiKey = "sk_test_key" }

Write-Output "Testing with API base: $url and API key: $apiKey"

Write-Output "Test 1: URL with Bearer"
curl -X POST "$url/api/voice-detection" `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer $apiKey" `
  -d '{"language":"English","audioFormat":"mp3","audioUrl":"https://file-examples.com/wp-content/uploads/2017/11/file_example_MP3_700KB.mp3"}'

Write-Output "Test 2: URL with x-api-key"
curl -X POST "$url/api/voice-detection" `
  -H "Content-Type: application/json" `
  -H "x-api-key: '"$apiKey"'" `
  -d '{"language":"English","audioFormat":"mp3","audioUrl":"https://www.learningcontainer.com/wp-content/uploads/2020/02/Kalimba.mp3"}'

Write-Output "Test 3: Base64 with Bearer"
$b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("data\human\english\english_proto_000.mp3"))
curl -X POST "$url/api/voice-detection" `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer $apiKey" `
  -d '{"language":"English","audioFormat":"mp3","audioBase64":"'"$b64"'"}'

Write-Output "Test 4: Error - both inputs"
curl -X POST "$url/api/voice-detection" `
  -H "Content-Type: application/json" `
  -H "x-api-key: '"$apiKey"'" `
  -d '{"language":"English","audioFormat":"mp3","audioBase64":"'"$b64"'","audioUrl":"https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"}'

Write-Output "Test 5: Error - neither input"
curl -X POST "$url/api/voice-detection" `
  -H "Content-Type: application/json" `
  -H "x-api-key: '"$apiKey"'" `
  -d '{"language":"English","audioFormat":"mp3"}'

Write-Output "Test 6: Error - invalid URL"
curl -X POST "$url/api/voice-detection" `
  -H "Content-Type: application/json" `
  -H "x-api-key: '"$apiKey"'" `
  -d '{"language":"English","audioFormat":"mp3","audioUrl":"not-a-url"}'

Write-Output "Test 7: Error - no auth"
curl -X POST "$url/api/voice-detection" `
  -H "Content-Type: application/json" `
  -d '{"language":"English","audioFormat":"mp3","audioUrl":"https://file-examples.com/wp-content/uploads/2017/11/file_example_MP3_700KB.mp3"}'

Write-Output "Test 8: Error - invalid API key"
curl -X POST "$url/api/voice-detection" `
  -H "Content-Type: application/json" `
  -H "Authorization: Bearer wrong_key" `
  -d '{"language":"English","audioFormat":"mp3","audioUrl":"https://www.learningcontainer.com/wp-content/uploads/2020/02/Kalimba.mp3"}'

