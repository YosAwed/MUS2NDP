# MUS to NDP MML Converter

MUS形式の音楽ファイルをNDP互換のMML(Music Macro Language)形式に変換するPythonスクリプトです。
主にMDXゲーム音楽のMUS形式を、NDPで再生可能なMML形式に変換するために使用されます。

## 特徴

- シンプルなコマンドラインインターフェース
- MUS形式の複数トラックをサポート
- テンポ情報を正確に変換（MUSのテンポ値からBPMへの変換）
- ループコマンドの変換（MUSの`L`コマンドをNDPの`@L`形式に変換）
- 非互換コマンド（DコマンドやPコマンドなど）を自動的に除去
- ノート長をフレーム数またはティック数で出力可能
- オクターブオフセットの調整が可能
- サンプルファイル付きで簡単に動作確認が可能

## インストール

1. リポジトリをクローンします:
   ```bash
   git clone https://github.com/yosawed/MDXMUS2NDP.git
   cd MDXMUS2NDP
   ```

2. 必要なパッケージをインストールします:
   ```bash
   pip install -r requirements.txt
   ```

## 使い方

MUSファイルをMMLに変換するには、以下のコマンドを実行します:

```bash
python mus2ndp.py input.mus -o output.mml
```

詳細なデバッグ情報を表示するには、`-v`オプションを使用します:

```bash
python mus2ndp.py input.mus -o output.mml -v
```

### サンプルファイルの実行

リポジトリに含まれるサンプルファイルを使って変換を試すには:

```bash
python mus2ndp.py samples/sample.mus -o output.mml -v
```

これにより、`samples/sample.mus` が `output.mml` に変換されます。

## 出力形式

出力されるMMLの形式は以下の通りです:

```
#TITLE "曲のタイトル"
#COMPOSER "作曲者名"
#TIMEBASE 48
123 T163

// トラック A (チャンネル 1)
1 v13q8o5c12<a+12f+12e12c12<a+12f+2&f+2.&f+8g8 @L o3a+8a16a+16f+2.&f+2.&
1 f+8g8a+8a16a+16f+2.&f+2&f+8q4>f8e8c8q8o4g+16g+16g+16g+16g+8...
```

## コマンドラインオプション

```
使用方法: python mus2ndp.py [オプション] 入力ファイル

引数:
  入力ファイル            入力MUSファイルのパス

オプション:
  -o, --output OUTPUT     出力MMLファイルのパス（省略時は入力ファイル名.mml）
  -m, --mode {default,direct_8track}
                         変換モード（デフォルト: default）
  -l, --length-mode {frames,ticks}
                         ノート長モード（デフォルト: frames）
  --octave-offset OCTAVE_OFFSET
                         オクターブオフセット（デフォルト: 0）
  -v, --verbose           詳細な出力を表示
  -h, --help             ヘルプメッセージを表示して終了
```

## 特記事項

### テンポ変換
MUSファイルの `@t` コマンド（例: `@t220`）は、NDP MMLのテンポコマンドに変換されます。変換式は以下の通りです：

```
bpm = round((60 * 4000000) / (40 * 1024 * (256 - TEMPO_MUS)))
```

例えば、`@t220` は `123 T163` に変換されます。`123`はアクティブなトラック番号（この場合はトラックA・B・Cが存在するため）を表します。

### ループコマンドの変換
MUSファイルの `L [...]` 形式のループコマンドは、NDP MMLの `@L ...` 形式に変換されます。括弧記号は削除されます。

### 非互換コマンドの除去
MUSファイルに含まれる以下のコマンドは、NDPでサポートされていないため自動的に削除されます：
- `D` コマンド（デチューンコマンド）
- `p` コマンド（パンポットコマンド）

## ライセンス
このプロジェクトは [LICENSE](LICENSE) ファイルに記載されたライセンスの下で公開されています。

// トラックA (チャンネル1)
A c4d4e4f4g4a4b4>c4

// トラックB (チャンネル2)
B c4d4e4f4g4a4b4>c4

// トラックC (チャンネル3)
C c4d4e4f4g4a4b4>c4
```

各トラックはMUSファイルのチャンネルA, B, C, ... に対応しています。

## 使い方

### 基本的な使い方:
```bash
python mdx_converter_logic.py input.mus -o output.mml
```

### オプション一覧:
```
usage: mdx_converter_logic.py [-h] [-o OUTPUT] [-m {default,direct_8track}]
                            [-l {frames,ticks}] [--verbose]
                            input_file

MUS to MML Converter

positional arguments:
  input_file            入力MUSファイルのパス

options:
  -h, --help            ヘルプを表示して終了します
  -o OUTPUT, --output OUTPUT
                        出力ファイルパス (デフォルト: <input_file>.mml)
  -m {default,direct_8track}, --mode {default,direct_8track}
                        変換モード (デフォルト: default)
  -l {frames,ticks}, --length-mode {frames,ticks}
                        ノート長の変換モード (デフォルト: frames)
  --verbose             詳細な出力を表示

### 変換モードの説明:

- `default`: 標準的なMML形式に変換します
- `direct_8track`: 8トラックのMML形式に直接マッピングして変換します
  --octave-offset OCTAVE_OFFSET
                        Octave offset for conversion (default: 0)
  -v, --verbose         Enable verbose output
```

## 例

基本的な変換:
```bash
python mdx_converter_logic.py sample.mdx
```

出力ファイルを指定:
```bash
python mdx_converter_logic.py sample.mus -o output.ndp
```

詳細モードで実行:
```bash
python mdx_converter_logic.py sample.mus -v
```

## トラブルシューティング

### 変換エラーが発生する場合
- 入力ファイルが正しいMUS形式であることを確認してください
- エラーメッセージを確認し、必要な修正を行ってください
- 問題が解決しない場合は、イシューを登録してください

## ライセンス

このプロジェクトはMITライセンスの下で公開されています。詳細は[LICENSE](LICENSE)ファイルを参照してください。

## 貢献方法

1. リポジトリをフォークします
2. フィーチャーブランチを作成します (`git checkout -b feature/AmazingFeature`)
3. 変更をコミットします (`git commit -m 'Add some AmazingFeature'`)
4. ブランチにプッシュします (`git push origin feature/AmazingFeature`)
5. プルリクエストを開きますて

バグレポートやプルリクエストは歓迎します。

## 作者

[Yoshiharu Dewa (Awed)]
