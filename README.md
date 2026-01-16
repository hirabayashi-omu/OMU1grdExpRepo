# 実験レポート作成アプリ

Streamlitを使用した実験レポート作成支援ツールです。

## デプロイ方法 (Streamlit Community Cloud)

1. **GitHubにリポジトリを作成**
   - このフォルダ内のファイルをGitHubリポジトリにアップロード（Push）してください。
   - 以下のファイルが必ず含まれていることを確認してください：
     - `app.py` (メインプログラム)
     - `requirements.txt` (ライブラリ設定)
     - `ipaexg.ttf` (PDF用日本語フォント)

2. **Streamlit Community Cloud にサインイン**
   - [Streamlit Community Cloud](https://share.streamlit.io/) にアクセスし、GitHubアカウントでサインインします。

3. **新しいアプリをデプロイ**
   - 「Create app」をクリックします。
   - 該当するGitHubリポジトリ、ブランチ（通常は`main`または`master`）、およびメインファイルパス（`app.py`）を選択します。

4. **デプロイ実行**
   - 「Deploy!」ボタンを押すと、数分で公開されます。

## ローカルでの実行方法

```bash
pip install -r requirements.txt
streamlit run app.py
```
