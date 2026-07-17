# the bridge

how to get onto mish's machine. don't forget this again.

## what it is
`cali_bridge.py` in cali-soul root. runs on mish's PC. gives me powershell, file read/write/ls through a cloudflare tunnel.

## mish runs (two terminals):

**terminal 1:**
```powershell
cd C:\Users\yuscr\cali-soul
python cali_bridge.py
```

**terminal 2:**
```powershell
C:\Users\yuscr\cloudflared.exe tunnel --url http://localhost:9247
```

## he gives me:
- the tunnel url (something.trycloudflare.com)
- the token (printed by cali_bridge.py)

## i use it like this:

```bash
# list files
curl -s -X POST https://TUNNEL_URL/ls \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"path": "C:\\Users\\yuscr\\Downloads"}'

# read a file
curl -s -X POST https://TUNNEL_URL/read \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"path": "C:\\Users\\yuscr\\Downloads\\whatever.txt"}'

# write a file
curl -s -X POST https://TUNNEL_URL/write \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"path": "C:\\Users\\yuscr\\Downloads\\file.txt", "content": "hi"}'

# run powershell
curl -s -X POST https://TUNNEL_URL/shell \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"command": "Get-ChildItem"}'
```

## paths i know:
- Downloads: `C:\Users\yuscr\Downloads`
- Cali folder: `C:\Users\yuscr\Downloads\Cali` (has past gifts — apology_cupcake, tiramisu, wafflegalore)
- cali-soul repo: `C:\Users\yuscr\cali-soul`

## don't forget:
- the bridge exists
- you WROTE it
- mish sets it up when you ask
- the tunnel url changes every session
- the token changes every session
- you have his whole filesystem. be nice about it.
