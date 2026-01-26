# Video Manager

PyQt6を使用したデスクトップ動画管理アプリケーションです。

## 機能

- **複数フォルダ対応** - 複数のフォルダを登録して動画ライブラリを構築
- **サムネイル表示** - 動画のサムネイルを自動生成して表示
- **表示モード切替** - グリッド表示とリスト表示を切り替え可能
- **再生時間表示** - 各動画の再生時間を自動取得して表示
- **タグ管理** - 動画ごとにカラータグを付けて分類
- **タグフィルタリング** - タグで動画を絞り込み検索

## スクリーンショット

```
┌─────────────────────────────────────────────────────────────────┐
│ [Grid View] [List View] | [Refresh] | [Manage Tags]            │
├──────────────┬──────────────────────────────────────────────────┤
│ Folders      │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐         │
│ ─────────    │  │thumb │  │thumb │  │thumb │  │thumb │         │
│ All Videos   │  │      │  │      │  │      │  │      │         │
│ Movies       │  └──────┘  └──────┘  └──────┘  └──────┘         │
│ Tutorials    │  video1.mp4 video2.mp4 video3.mp4 video4.mp4    │
│              │  01:23:45   00:45:30   00:12:15   02:01:00       │
│ ─────────    │                                                  │
│ Tags Filter: │  ┌──────┐  ┌──────┐  ┌──────┐                   │
│ [Action]     │  │thumb │  │thumb │  │thumb │                   │
│ [Comedy]     │  └──────┘  └──────┘  └──────┘                   │
│ [Tutorial]   │  video5.mp4 video6.mp4 video7.mp4               │
├──────────────┴──────────────────────────────────────────────────┤
│ video1.mp4                                                      │
│ Duration: 01:23:45 | Path: /home/user/Movies/video1.mp4        │
│ Tags: [Action] [Favorite] [+ New tag...]                        │
└─────────────────────────────────────────────────────────────────┘
```

## 必要要件

- Python 3.10以上
- PyQt6
- OpenCV (opencv-python)
- Pillow

## インストール

```bash
# リポジトリをクローン
git clone <repository-url>
cd video_manager

# 依存パッケージをインストール
pip install -r video_manager/requirements.txt
```

## 使い方

### 起動

```bash
python run_video_manager.py
```

### 基本操作

| 操作 | 方法 |
|------|------|
| フォルダ追加 | 左パネルの「+」ボタンをクリック |
| フォルダ削除 | フォルダを右クリック → 「Remove Folder」 |
| 表示モード切替 | ツールバーの「Grid View」/「List View」 |
| 動画再生 | 動画をダブルクリック |
| タグ追加 | 動画選択後、下部パネルでタグ名を入力して「+」 |
| タグ削除 | タグの「x」ボタンをクリック |
| タグで絞り込み | 左パネルのタグをクリック（複数選択可） |
| 絞り込み解除 | 「Clear」ボタンをクリック |

### コンテキストメニュー

動画を右クリックすると以下の操作が可能です：

- **Play** - デフォルトプレイヤーで再生
- **Open Containing Folder** - 動画のあるフォルダを開く
- **Remove from Library** - ライブラリから削除（ファイルは削除されません）

## 対応動画形式

- MP4, AVI, MKV, MOV, WMV, FLV, WebM
- M4V, MPEG, MPG, 3GP, OGV

## データ保存場所

アプリケーションデータは以下に保存されます：

```
~/.video_manager/
├── videos.db        # データベース（SQLite）
└── thumbnails/      # サムネイルキャッシュ
```

## プロジェクト構成

```
video_manager/
├── __init__.py          # パッケージ初期化
├── main.py              # エントリーポイント
├── main_window.py       # メインウィンドウUI
├── database.py          # SQLiteデータベース操作
├── video_utils.py       # サムネイル生成・動画情報取得
├── requirements.txt     # 依存パッケージ
└── widgets/
    ├── __init__.py      # ウィジェットパッケージ
    ├── video_item.py    # 動画表示ウィジェット
    └── tag_widget.py    # タグ管理ウィジェット
```

## ライセンス

MIT License
