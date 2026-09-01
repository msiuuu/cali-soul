$r = Invoke-WebRequest -Uri "https://www.pornhub.com/video/search?search=korean+girl+bbc" -UseBasicParsing -TimeoutSec 15
$r.Content.Substring(0, [Math]::Min(3000, $r.Content.Length))