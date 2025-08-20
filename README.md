## 🚀 クイックスタート

### 1. 環境設定

```bash
# リポジトリクローン
git clone <repository-url>
cd internal

# Python仮想環境作成・有効化
python -m venv venv
source venv/bin/activate  # macOS/Linux
# または
venv\Scripts\activate     # Windows

# 必要なパッケージインストール
pip install -r requirements.txt
```

### 2. データ生成

**運航候補別の最適収益・優先順位データ**の生成:

```bash
# 全航空会社データ生成
python scripts/generate_candidate_data.py

# 特定航空会社のみ生成
python scripts/generate_candidate_data.py airline_01
python scripts/generate_candidate_data.py airline_02
# ... airline_15まで
```

## 📁 プロジェクト構造

```
internal/
├── scripts/
│   └── generate_candidate_data.py    # メインデータ生成スクリプト
├── output/                           # 生成されたデータ（gitから除外）
│   ├── airline_01/
│   │   ├── internal_resource_data.json
│   │   ├── profile.py
│   │   └── analytics_data/
│   │       └── candidate/
│   │           ├── international/
│   │           │   ├── international_departure.xlsx
│   │           │   └── international_arrival.xlsx
│   │           └── domestic/
│   │               └── domestic_all.xlsx
│   └── ... (airline_02 ~ airline_15)
└── requirements.txt                  # Pythonパッケージ依存関係
```
