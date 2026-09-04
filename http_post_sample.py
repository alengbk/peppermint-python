# 建立工單命令列工具 (CLI)
# 範例：python create_ticket.py --title "Server Down" --detail "Main database unreachable" --priority critical --type incident

import argparse
import sys
import requests

BASE = 'http://127.0.0.1:5003'
DEFAULT_API_KEY = (
    'pep_c7504d551a27f7c74517a4d53ecfd41da023df6faee3f5eee951ed8625fd1400'
)


def main():
  parser = argparse.ArgumentParser(description='透過 API 建立工單')
  parser.add_argument(
      '--title', required=True, help='工單標題，例如 Disk 95%%'
  )
  parser.add_argument(
      '--detail', required=True, help='工單詳細說明，例如 /dev/sda1 usage 95%%'
  )
  parser.add_argument(
      '--priority',
      default='medium',
      choices=['low', 'medium', 'high', 'critical'],
      help='優先權 (預設: medium)',
  )
  parser.add_argument(
      '--type',
      default='incident',
      choices=['incident', 'support', 'task'],
      help='工單類型 (預設: incident)',
  )
  parser.add_argument(
      '--api-key', default=DEFAULT_API_KEY, help='API Key 授權金鑰'
  )
  parser.add_argument('--base-url', default=BASE, help='API 基礎網址')

  args = parser.parse_args()

  headers = {
      'Authorization': f'Bearer {args.api_key}',
      'Content-Type': 'application/json',
  }

  payload = {
      'title': args.title,
      'detail': args.detail,
      'priority': args.priority,
      'type': args.type,
  }

  try:
    r = requests.post(
        f'{args.base_url}/api/v1/ticket', json=payload, headers=headers
    )
    r.raise_for_status()
    d = r.json()
    print(
        f'✅ #{d["number"]} - {d["title"]} (dedupCount={d["dedupCount"]},'
        f' source={d["createdBy"]["role"]})'
    )
  except requests.exceptions.ConnectionError:
    print(
        f'❌ 連線失敗: 無法連線至伺服器 ({args.base_url})。請確認 API'
        ' 伺服器是否已啟動。',
        file=sys.stderr,
    )
    sys.exit(1)
  except requests.exceptions.RequestException as e:
    print(f'❌ 建立工單失敗: {e}', file=sys.stderr)
    if 'r' in locals() and r.text:
      print(f'回應內容: {r.text}', file=sys.stderr)
    sys.exit(1)


if __name__ == '__main__':
  main()
