# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, date
import json
from io import BytesIO
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
import base64

# === PDF 用 日本語フォント ===
pdfmetrics.registerFont(TTFont('IPAexGothic', 'ipaexg.ttf'))

# === Matplotlib 用 日本語フォント ===
from matplotlib import font_manager, rcParams
font_manager.fontManager.addfont("ipaexg.ttf")
rcParams["font.family"] = "IPAexGothic"
# -----------------------
# ダイアログ・共通処理
# -----------------------

# テーマごとに管理するデータキー
EXP_DATA_KEYS = [
    "tools_list", "references_list", "evaluation_method",
    "melting_point_df", "result_df", "lit_cu", "lit_al", "lit_sus", "thermal_conductivity_ref", "comparison_text", "apparatus_photo_data",
    "fc_charge_df", "fc_discharge_1", "fc_discharge_2", "fc_discharge_3", "fc_comparison_text",
    "wt_original_water_photo", "wt_proto1_dev_photo", "wt_proto1_water_photo", "wt_proto1_text", "wt_proto2_dev_photo", "wt_proto2_water_photo", "wt_proto2_text", "wt_clarity_df", "wt_coagulation_photo", "wt_coagulation_text", "wt_comparison_text"
]

def get_current_exp_state():
    """現在のテーマに関連するステートを辞書にまとめる"""
    state = {}
    for k in EXP_DATA_KEYS:
        if k in st.session_state:
            val = st.session_state[k]
            # DataFrameは辞書に変換
            if isinstance(val, pd.DataFrame):
                state[k] = val.to_dict(orient="records")
            else:
                state[k] = val
    # 設問データも追加
    for k, v in st.session_state.items():
        if k.startswith("設問_"):
            state[k] = v
    return state

def apply_exp_state(state):
    """辞書からステートを復元する"""
    if not state:
        reset_experiment_data()
        return

    for k, v in state.items():
        if k in EXP_DATA_KEYS or k.startswith("設問_"):
            # テーブル系はDataFrameに再変換
            df_cols = {
                "tools_list": ["器具・装置・薬品名", "用途・役割など"],
                "references_list": ["書籍名・サイト名", "著者・発行者", "発行年・URL"],
                "fc_discharge_1": None, "fc_discharge_2": None, "fc_discharge_3": None,
                "melting_point_df": None, "result_df": None, "fc_charge_df": None, "wt_clarity_df": None
            }
            if k in df_cols:
                df = pd.DataFrame(v)
                if df_cols[k] and df.empty:
                    df = pd.DataFrame(columns=df_cols[k])
                st.session_state[k] = df
            else:
                st.session_state[k] = v
    
    # ロードされなかったキーはデフォルトに戻す
    for k in EXP_DATA_KEYS:
        if k not in state:
            # 各キーごとのデフォルト処理（簡易化のためresetの一部を流用）
            pass # 必要なら個別実装

@st.dialog("⚠️ 実験タイトルの切り替え")
def confirm_exp_title_change_dialog(new_title):
    st.warning(f"実験タイトルを「{new_title}」に切り替えますか？")
    st.markdown("切り替えると、表示される入力項目が変化します。現在のデータはアプリ内に一時保存され、後で戻ることも可能です。")
    col1, col2 = st.columns(2)
    if col1.button("切り替える", use_container_width=True):
        # 現在のデータを退避
        old_title = st.session_state.exp_title
        if "experiment_registry" not in st.session_state:
            st.session_state.experiment_registry = {}
        st.session_state.experiment_registry[old_title] = get_current_exp_state()
        
        # タイトル更新
        st.session_state.exp_title = new_title
        
        # 新しいタイトルのデータを復元（なければ初期化）
        if new_title in st.session_state.experiment_registry:
            apply_exp_state(st.session_state.experiment_registry[new_title])
        else:
            reset_experiment_data()
            
        if "exp_title_selector" in st.session_state:
            st.session_state.exp_title_selector = new_title
        st.rerun()
    if col2.button("キャンセル", use_container_width=True):
        if "exp_title_selector" in st.session_state:
            st.session_state.exp_title_selector = st.session_state.exp_title
        st.rerun()

@st.dialog("⚠️ JSONからの復元")
def confirm_json_restore_dialog(uploaded_file):
    st.warning("ファイルを読み込んで復元しますか？")
    st.markdown("**現在入力している内容はすべて上書きされます。**")
    col1, col2 = st.columns(2)
    if col1.button("復元を実行", use_container_width=True):
        perform_json_restore(uploaded_file)
        st.rerun()
    if col2.button("キャンセル", use_container_width=True):
        st.rerun()

def perform_json_restore(uploaded_file):
    try:
        data = json.load(uploaded_file)
        
        # 基本情報
        if "global_info" in data:
            g = data["global_info"]
            if "exp_date" in g: st.session_state.exp_date = datetime.fromisoformat(g["exp_date"]).date()
            if "class_name" in g: st.session_state.class_name = g["class_name"]
            if "seat_number" in g: st.session_state.seat_number = g["seat_number"]
            if "student_id" in g: st.session_state.student_id = g["student_id"]
            if "student_name" in g: st.session_state.student_name = g["student_name"]
            if "partner1_id" in g: st.session_state.partner1_id = g["partner1_id"]
            if "partner1_name" in g: st.session_state.partner1_name = g["partner1_name"]
            if "partner2_id" in g: st.session_state.partner2_id = g["partner2_id"]
            if "partner2_name" in g: st.session_state.partner2_name = g["partner2_name"]

        # レジストリ（全テーマのデータ）
        if "experiment_registry" in data:
            st.session_state.experiment_registry = data["experiment_registry"]
            # 現在のタイトルに合わせたデータをカレントに反映
            cur_title = st.session_state.exp_title
            if cur_title in st.session_state.experiment_registry:
                apply_exp_state(st.session_state.experiment_registry[cur_title])
        else:
            # 互換性維持：registryがない場合はトップレベルのデータをカレントとして扱う
            apply_exp_state(data)

        # タイトルセレクター同期
        if "exp_title_selector" in st.session_state:
            st.session_state.exp_title_selector = st.session_state.exp_title

        st.success("JSONを読み込みました")
    except Exception as e:
        st.error(f"読み込みエラー: {e}")

def reset_experiment_data():
    # 完全に空の状態へリセット（共通含む）
    st.session_state.tools_list = pd.DataFrame(columns=["器具・装置・薬品名", "用途・役割など"])
    st.session_state.references_list = pd.DataFrame({
        "書籍名・サイト名": ["物理基礎 改訂版", "国立天文台 理科年表オフィシャルサイト"],
        "著者・発行者": ["第一学習社", "国立天文台"],
        "発行年・URL": ["2023年", "https://official.rikanenpyo.jp/"]
    })
    st.session_state.evaluation_method = ""
    # Exp 1
    st.session_state.melting_point_df = pd.DataFrame({
        "1回目(℃)": [""], "2回目(℃)": [""], "3回目(℃)": [""], "平均(℃)": [""]
    }, index=["融解温度(℃)"])
    st.session_state.result_df = pd.DataFrame({
        "距離(cm)": [2, 4, 6, 8, 10, 12],
        "銅(sec)": [""]*6, "アルミ(sec)": [""]*6, "ステンレス(sec)": [""]*6
    })
    st.session_state.lit_cu = ""; st.session_state.lit_al = ""; st.session_state.lit_sus = ""
    st.session_state.thermal_conductivity_ref = ""; st.session_state.comparison_text = ""
    st.session_state.apparatus_photo_data = None
    # Exp 2
    st.session_state.fc_charge_df = pd.DataFrame({
        "充電時間(sec)": ["","",""], "充電電圧(V)": ["","",""], "開回路電圧(V)": ["","",""]
    }, index=["1回目", "2回目", "3回目"])
    st.session_state.fc_discharge_1 = init_discharge_df()
    st.session_state.fc_discharge_2 = init_discharge_df()
    st.session_state.fc_discharge_3 = init_discharge_df()
    st.session_state.fc_comparison_text = ""
    # Exp 3
    st.session_state.wt_original_water_photo = None; st.session_state.wt_proto1_dev_photo = None
    st.session_state.wt_proto1_water_photo = None; st.session_state.wt_proto1_text = ""
    st.session_state.wt_proto2_dev_photo = None; st.session_state.wt_proto2_water_photo = None
    st.session_state.wt_proto2_text = ""
    st.session_state.wt_clarity_df = pd.DataFrame({"試作検討①": [""], "試作検討②": [""]}, index=["清澄度"])
    st.session_state.wt_coagulation_photo = None; st.session_state.wt_coagulation_text = ""
    st.session_state.wt_comparison_text = ""
    # Questions
    for k in list(st.session_state.keys()):
        if k.startswith("設問_"): st.session_state[k] = ""
    # Clear editors
    for key in ["tools_list_editor", "references_list_editor", "melting_point_editor", "result_df_editor", "wt_clarity_editor", "fc_charge_editor", "fc_d1_editor", "fc_d2_editor", "fc_d3_editor"]:
        if key in st.session_state: del st.session_state[key]

def create_proportional_image(img_io, max_width=100*mm, max_height=75*mm):
    """アスペクト比を維持しつつ、指定の枠内に収まるReportLab Imageを作成する"""
    try:
        img_reader = ImageReader(img_io)
        iw, ih = img_reader.getSize()
        aspect = ih / float(iw)
        
        width = max_width
        height = width * aspect
        
        if height > max_height:
            height = max_height
            width = height / aspect
            
        return Image(img_io, width=width, height=height)
    except:
        # 失敗時はデフォルトサイズで返す
        return Image(img_io, width=max_width, height=max_height)


# -----------------------
# 初期化関数
# -----------------------
def init_state(key, default):
    if key not in st.session_state:
        st.session_state[key] = default

# -----------------------
# グラフ作成関数
# -----------------------
def create_graph():
    plt.rcParams["font.family"] = "IPAexGothic" # PDF用にもIPAフォントが安全だが、環境による。一旦汎用日本語フォント
    # Streamlit Cloud等ではIPAexGothicがシステムに入っていない場合があるが、
    # ここではローカル実行前提またはipaexg.ttf利用前提で進める
    
    # 既に登録済みのipaexg.ttfをMatplotlibで使うのは少々手間(FontProperties等)。
    # 簡易的に "Yu Gothic" や "Meiryo" 等、Windows標準をトライしつつ、
    # フォールバックする実装が望ましいが、今回は既存コードの "Yu Gothic" を踏襲。
    plt.rcParams["font.family"] = "Yu Gothic"
    
    fig, ax = plt.subplots(figsize=(6,4))
    
    df = st.session_state.result_df
    # X軸
    x = pd.to_numeric(df["距離(cm)"], errors="coerce")
    
    # プロット
    legend_labels = []
    for col, label, color in zip(
        ["銅(sec)", "アルミ(sec)", "ステンレス(sec)"],
        ["銅", "アルミ", "ステンレス"],
        ["#ff7f0e", "#1f77b4", "#7f7f7f"] # 簡易的な色指定(matplotlib default準拠)
    ):
        y = pd.to_numeric(df[col], errors="coerce")
        mask = ~y.isna()
        if mask.any() and (~x.isna()).any(): # xもvalidである必要あり
             # xとyのindex整合性を取るため、df全体でmaskする方が安全だが
             # ここでは簡易的に直列データとして扱う(df構造が保証されている前提)
             # xのmaskも考慮
             valid_indices = mask & ~x.isna()
             if valid_indices.any():
                ax.plot(x[valid_indices], y[valid_indices], marker="o", label=label, color=color)
                legend_labels.append(label)

    ax.set_ylabel("融解時間 (sec)")
    ax.grid(True)
    if legend_labels:
        ax.legend()
    return fig

def create_fuel_cell_graph():
    plt.rcParams["font.family"] = "Yu Gothic"
    fig, ax = plt.subplots(figsize=(6,4))
    
    # 3回分のデータをプロット
    colors = ["#ff7f0e", "#1f77b4", "#2ca02c"]
    labels = ["1回目", "2回目", "3回目"]
    dfs = [st.session_state.fc_discharge_1, st.session_state.fc_discharge_2, st.session_state.fc_discharge_3]
    
    has_plot = False
    for i, df in enumerate(dfs):
        try:
             # 時間(sec) vs 出力(mW)
             t = pd.to_numeric(df["放電時間(sec)"], errors="coerce")
             # 出力列は "出力(mW)" を使用
             p = pd.to_numeric(df["出力(mW)"], errors="coerce")
             
             mask = ~t.isna() & ~p.isna()
             if mask.any():
                 ax.plot(t[mask], p[mask], marker="o", label=labels[i], color=colors[i])
                 has_plot = True
        except Exception:
            pass

    ax.set_xlabel("放電時間 (sec)")
    ax.set_ylabel("出力 (mW)") # ≒ エネルギー的な指標として出力を使用
    ax.grid(True)
    if has_plot:
        ax.legend()
    return fig

# -----------------------
# 初期化
# -----------------------
init_state("exp_title", "実験① 熱の可視化")
init_state("experiment_registry", {})
init_state("exp_date", date.today())
init_state("class_name", "1年1組")
init_state("seat_number", "00")
init_state("student_id", "00")
init_state("student_name", "高専 太郎")
init_state("partner1_id", "")
init_state("partner1_name", "")
init_state("partner2_id", "")
init_state("partner2_name", "")
init_state("tools_list", pd.DataFrame(columns=["器具・装置・薬品名", "用途・役割など"]))
init_state("evaluation_method", "")
init_state("melting_point_df", pd.DataFrame({
    "1回目(℃)": [""],
    "2回目(℃)": [""],
    "3回目(℃)": [""],
    "平均(℃)": [""]
}, index=["融解温度(℃)"]))
init_state("references_list", pd.DataFrame({
    "書籍名・サイト名": ["物理基礎 改訂版", "国立天文台 理科年表オフィシャルサイト"],
    "著者・発行者": ["第一学習社", "国立天文台"],
    "発行年・URL": ["2023年", "https://official.rikanenpyo.jp/"]
}))
init_state("result_df", pd.DataFrame({
    "距離(cm)": [2, 4, 6, 8, 10, 12],
    "銅(sec)": [""]*6,
    "アルミ(sec)": [""]*6,
    "ステンレス(sec)": [""]*6
}))
init_state("literature_values", {"銅":"","アルミ":"","ステンレス":""})
init_state("thermal_conductivity_ref", "")
init_state("comparison_text", "")
init_state("photos", [])
init_state("apparatus_photo_data", None) # base64 string or bytes for persistence

# 文献値UI用
init_state("lit_cu", st.session_state.literature_values.get("銅", ""))
init_state("lit_al", st.session_state.literature_values.get("アルミ", ""))
init_state("lit_sus", st.session_state.literature_values.get("ステンレス", ""))

# 実験2用の状態初期化
# 充電実験
init_state("fc_charge_df", pd.DataFrame({
    "充電時間(sec)": ["","",""],
    "充電電圧(V)": ["","",""],
    "開回路電圧(V)": ["","",""]
}, index=["1回目", "2回目", "3回目"]))

# 放電実験 (共通フォーマット)
def init_discharge_df():
    return pd.DataFrame({
        "放電時間(分)": [0, 5, 10, 15],
        "放電時間(sec)": [0, 300, 600, 900],
        "端子電圧(V)": ["","","",""],
        "電流(mA)": ["","","",""],
        "出力(mW)": ["","","",""] # 「エネルギー(J)」列の代替として出力(mW)を使用し、面積でJを議論
    })

init_state("fc_discharge_1", init_discharge_df())
init_state("fc_discharge_2", init_discharge_df())
init_state("fc_discharge_3", init_discharge_df())
init_state("fc_comparison_text", "") # 実験2用の考察

# 実験3用の状態初期化
init_state("wt_original_water_photo", None)
init_state("wt_proto1_dev_photo", None)
init_state("wt_proto1_water_photo", None)
init_state("wt_proto1_text", "")
init_state("wt_proto2_dev_photo", None)
init_state("wt_proto2_water_photo", None)
init_state("wt_proto2_text", "")
init_state("wt_clarity_df", pd.DataFrame({
    "試作検討①": [""],
    "試作検討②": [""]
}, index=["清澄度"]))
init_state("wt_coagulation_photo", None)
init_state("wt_coagulation_text", "")
init_state("wt_comparison_text", "")

# -----------------------
# 設問辞書
# -----------------------
QUESTION_DICT = {
    "実験① 熱の可視化": {
        "熱伝導って何？": ["高温","低温","エネルギー"],
        "固体の中で熱が伝わる仕組みは？": ["原子","格子振動","自由電子"],
        "物質による伝わりやすさの違いは？": ["熱伝導率","流体","断熱材"]
    },
    "実験② アルカリ型燃料電池の組み立て": {
        "アルカリ型燃料電池って何？": ["水素","アルカリ","水"],
        "電池で発電できる仕組みは？": ["材料の反応性の違い","起電力","電子やイオンの動き"],
        "組み立てで大切な工夫は？": ["触媒","安全上気を付けること"]
    },
    "実験③ 水処理装置の設計と提案": {
        "水の利用と機械の関係": ["浄水","下水","ポンプ"],
        "水の汚れとは？水を綺麗にする仕組み": [],
        "作製した装置で工夫したポイント": []
    }
}
# -----------------------
# 採点ロジック関数
# -----------------------
def calculate_achievement_rate():
    score_home = 0.0
    score_report = 0.0
    
    # 1. 自宅課題 (50%)
    # 設問回答 (40%)
    q_dict = QUESTION_DICT.get(st.session_state.exp_title, {})
    if q_dict:
        pts_per_q = 40.0 / len(q_dict)
        for q, words in q_dict.items():
            key_name = "設問_" + q.replace("？","").replace(" ","_")
            ans = str(st.session_state.get(key_name, ""))
            
            # (1) 入力あり: 30%
            if ans.strip():
                score_home += pts_per_q * 0.3
            
            # (2) 200文字以上: 40%
            if len(ans) >= 200:
                score_home += pts_per_q * 0.4
            elif len(ans) >= 100: # 部分点
                score_home += pts_per_q * 0.2
            
            # (3) 必須語句: 30%
            if words:
                all_found = True
                for w in words:
                    if w not in ans:
                        all_found = False
                        break
                if all_found:
                    score_home += pts_per_q * 0.3

    # 参考文献 (10%)
    has_ref = False
    default_titles = ["物理基礎 改訂版", "国立天文台 理科年表オフィシャルサイト"]
    
    if not st.session_state.references_list.empty:
        for _, row in st.session_state.references_list.iterrows():
             title = str(row.get("書籍名・サイト名", "")).strip()
             # 空白でなく、かつデフォルト例そのままでない場合のみ加点対象とする
             if title and (title not in default_titles):
                 has_ref = True
                 break
    if has_ref:
        score_home += 10.0

    # 2. レポート点 (50%)
    # 基本情報 (5%)
    # デフォルト値の確認
    is_default_basic = (st.session_state.student_id == "00") or (st.session_state.student_name == "高専 太郎")
    
    if st.session_state.class_name and st.session_state.student_id and st.session_state.student_name:
        # デフォルトのままなら加点しない
        if not is_default_basic:
            score_report += 5.0
    
    # 実験方法 (10%)
    # 器具 (4%)
    has_tools = False
    if not st.session_state.tools_list.empty:
        for _, row in st.session_state.tools_list.iterrows():
             if str(row.iloc[0]).strip():
                 has_tools = True
                 break
    if has_tools: score_report += 4.0
    
    # 写真 (4%)
    if st.session_state.exp_title == "実験③ 水処理装置の設計と提案":
        # 試作①か②の装置写真があれば加点
        if st.session_state.wt_proto1_dev_photo or st.session_state.wt_proto2_dev_photo:
            score_report += 4.0
    else:
        if st.session_state.apparatus_photo_data:
            score_report += 4.0
    
    # 評価方法 (2%)
    if st.session_state.exp_title == "実験③ 水処理装置の設計と提案":
        # 清澄度の入力があれば加点
        c_df = st.session_state.wt_clarity_df
        try:
            # clean index issue using iloc
            if str(c_df.iloc[0]["試作検討①"]).strip() or str(c_df.iloc[0]["試作検討②"]).strip():
                score_report += 2.0
        except: pass
    else:
        if st.session_state.evaluation_method:
            score_report += 2.0

    if st.session_state.exp_title == "実験① 熱の可視化":
        # 実験結果 (20%)
        # 融解平均 (5%)
        try:
            m_idx = st.session_state.melting_point_df.index[0]
            if str(st.session_state.melting_point_df.at[m_idx, "平均(℃)"]).strip():
                 score_report += 5.0
        except:
            pass
            
        # 結果データ (15%)
        r_cols = ["銅(sec)", "アルミ(sec)", "ステンレス(sec)"]
        total_cells = len(st.session_state.result_df) * 3
        filled_cells = 0
        for c in r_cols:
            for v in st.session_state.result_df[c]:
                if str(v).strip():
                    filled_cells += 1
        if total_cells > 0:
            score_report += 15.0 * (filled_cells / total_cells)

        # 考察 (15%)
        # 文献値 (5%)
        if st.session_state.lit_cu and st.session_state.lit_al and st.session_state.lit_sus:
            score_report += 5.0
        
        # 引用 (2%)
        if st.session_state.thermal_conductivity_ref:
            score_report += 2.0
        
        # 本文 (8%)
        if len(st.session_state.comparison_text) > 20: 
            score_report += 8.0

    elif st.session_state.exp_title == "実験② アルカリ型燃料電池の組み立て":
        # 実験結果 (20%)
        # 充電データあり (5%)
        filled_charge = 0
        for c in ["充電時間(sec)", "充電電圧(V)", "開回路電圧(V)"]:
             for v in st.session_state.fc_charge_df[c]:
                 if str(v).strip(): filled_charge += 1
        if filled_charge > 5: # ある程度埋まっていれば
             score_report += 5.0

        # 放電データ (15%)
        # 3回分、各4行。
        filled_discharge = 0
        total_slots = 3 * 4 * 2 # 電圧・電流の2項目 * 4行 * 3回
        for df in [st.session_state.fc_discharge_1, st.session_state.fc_discharge_2, st.session_state.fc_discharge_3]:
             for c in ["端子電圧(V)", "電流(mA)"]:
                 for v in df[c]:
                     if str(v).strip(): filled_discharge += 1
        if total_slots > 0:
            score_report += 15.0 * (filled_discharge / total_slots)

        # 考察 (15%)
        # 本文のみ (15%)
        if len(st.session_state.fc_comparison_text) > 20:
            score_report += 15.0

    elif st.session_state.exp_title == "実験③ 水処理装置の設計と提案":
         # 実験結果 (20%)
         # 写真の有無 (10%)
         photo_count = 0
         for k in ["wt_original_water_photo", "wt_proto1_dev_photo", "wt_proto1_water_photo", 
                   "wt_proto2_dev_photo", "wt_proto2_water_photo", "wt_coagulation_photo"]:
             if st.session_state.get(k): photo_count += 1
         
         if photo_count >= 6: score_report += 10.0
         elif photo_count >= 3: score_report += 5.0
         
         # 記述とデータ (10%)
         item_count = 0
         if len(st.session_state.wt_proto1_text) > 10: item_count += 1
         if len(st.session_state.wt_proto2_text) > 10: item_count += 1
         if len(st.session_state.wt_coagulation_text) > 10: item_count += 1
         
         # 清澄度
         c_df = st.session_state.wt_clarity_df
         try:
             if str(c_df.iloc[0]["試作検討①"]).strip() and str(c_df.iloc[0]["試作検討②"]).strip():
                 item_count += 1
         except: pass
             
         score_report += 10.0 * (item_count / 4.0)
         
         # 考察 (15%)
         if len(st.session_state.wt_comparison_text) > 20:
             score_report += 15.0

    return int(score_home), int(score_report), int(score_home + score_report), is_default_basic

# -----------------------
# ページ設定
# -----------------------
st.set_page_config(page_title="実験レポート作成", layout="wide")
st.markdown("""
    <div style='text-align: center; margin-bottom: 20px;'>
        <h2 style='margin:0; font-size: 1.8em;'>🧪 総合工学システム実習 レポート作成（M2）</h2>
        <p style='margin:5px 0 0 0; font-size: 1.0em; color: gray;'>（大阪公立大学工業高等専門学校 1年）</p>
    </div>
""", unsafe_allow_html=True)

# -----------------------
# サイドバー
# -----------------------
# -----------------------
# サイドバー
# -----------------------
with st.sidebar:
    st.header("操作メニュー")
    
    st.info("💡 **入力のヒント**：\n各項目は入力後に **Enterキー** を押すか、ボックス外をクリックすると確定・反映されます。")

    # 1. 入力状態の復元／保存
    with st.container(border=True):
        st.markdown("#### ① 入力状態の復元／保存")
        
        # JSON復元
        st.markdown("**JSONから復元**")
        uploaded_file = st.file_uploader("ファイルをアップロード", type="json", key="json_loader", label_visibility="collapsed")

        if uploaded_file is not None:
            if st.button("以前の入力状態を復元"):
                confirm_json_restore_dialog(uploaded_file)
        
        # 元の復元ロジックは perform_json_restore に集約したため削除またはコメントアウト
        # ここでは perform_json_restore を通じた dialog 呼び出しのみ行う

        st.divider()

        # JSON保存
        st.markdown("**JSON保存**")
        if st.button("現在の入力状態を保存"):
            # 現在のタイトルのデータを最新にするため、レジストリを更新
            if "experiment_registry" not in st.session_state:
                st.session_state.experiment_registry = {}
            st.session_state.experiment_registry[st.session_state.exp_title] = get_current_exp_state()

            home_score, report_score, total_score, _ = calculate_achievement_rate()

            # 基本情報
            global_info = {
                "exp_date": st.session_state.exp_date.isoformat(),
                "class_name": st.session_state.class_name,
                "seat_number": st.session_state.seat_number,
                "student_id": st.session_state.student_id,
                "student_name": st.session_state.student_name,
                "partner1_id": st.session_state.partner1_id,
                "partner1_name": st.session_state.partner1_name,
                "partner2_id": st.session_state.partner2_id,
                "partner2_name": st.session_state.partner2_name,
                "last_exp_title": st.session_state.exp_title
            }

            export_data = {
                "global_info": global_info,
                "achievement_at_save": {
                    "home": home_score,
                    "report": report_score,
                    "total": total_score
                },
                "experiment_registry": st.session_state.experiment_registry
            }

            title_safe = st.session_state.exp_title.replace(" ", "_").replace("　", "_")
            name_safe = st.session_state.student_name.replace(" ", "_").replace("　", "_")
            timestamp = datetime.now().strftime('%Y%m%d%H%M')
            st.session_state["json_export_data"] = json.dumps(export_data, ensure_ascii=False, indent=2)
            st.session_state["json_file_name"] = f"{st.session_state.student_id}_{name_safe}_{timestamp}.json"
            st.success("全てのテーマのデータ（レジストリ）を保存しました。別の実験に切り替えてもデータは保持されます。")

        if "json_export_data" in st.session_state:
            st.download_button(
                "保存状態のダウンロード",
                data=st.session_state["json_export_data"],
                file_name=st.session_state.get("json_file_name", "report.json"),
                mime="application/json"
            )

    # 2. 実験結果のまとめ
    with st.container(border=True):
        st.markdown("#### ② 実験結果のまとめ")
        
        st.markdown("**PDF作成**")
        if st.button("提出用ファイルの作成"):
            try:
                buffer = BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=A4)
                elements = []
                styles = getSampleStyleSheet()

                # 日本語フォント設定
                styles['Normal'].fontName = 'IPAexGothic'
                styles['Title'].fontName = 'IPAexGothic'
                styles['Heading2'].fontName = 'IPAexGothic'
                
                # スコア計算
                home_score, report_score, total_score, _ = calculate_achievement_rate()
                score_text = f"簡易自己評価: {total_score}% (自宅課題: {home_score}% / レポート: {report_score}%)"
                score_style = ParagraphStyle('Score', parent=styles['Normal'], alignment=TA_RIGHT, textColor=colors.red)
                elements.append(Paragraph(score_text, score_style))
                elements.append(Spacer(1, 5*mm))

                # タイトル・基本情報
                elements.append(Paragraph(f"実験タイトル: {st.session_state.exp_title}", styles['Title']))
                elements.append(Paragraph(f"実験日: {st.session_state.exp_date}", styles['Normal']))
                
                # 本人情報
                elements.append(Paragraph(
                    f"クラス: {st.session_state.class_name} 席番号: {st.session_state.seat_number} "
                    f"出席番号: {st.session_state.student_id} 氏名: {st.session_state.student_name}", 
                    styles['Normal']
                ))
                
                # 共同実験者情報（入力がある場合のみ表示）
                partners = []
                if st.session_state.partner1_id or st.session_state.partner1_name:
                    partners.append(f"共同実験者①: {st.session_state.partner1_id} {st.session_state.partner1_name}")
                if st.session_state.partner2_id or st.session_state.partner2_name:
                    partners.append(f"共同実験者②: {st.session_state.partner2_id} {st.session_state.partner2_name}")
                
                if partners:
                    elements.append(Paragraph(" / ".join(partners), styles['Normal']))
                
                elements.append(Spacer(1,5*mm))

                # 1. 調査レポート（自宅課題）
                elements.append(Paragraph("1. 調査レポート（自宅課題）", styles['Heading2']))
                for q in QUESTION_DICT[st.session_state.exp_title]:
                    key_name = "設問_" + q.replace("？","").replace(" ","_")
                    answer = st.session_state.get(key_name,"")
                    elements.append(Paragraph(f"<b>Q. {q}</b>", styles['Normal']))
                    elements.append(Paragraph(f"A. {answer}", styles['Normal']))
                    elements.append(Spacer(1, 2*mm))
                
                # 参考文献
                elements.append(Paragraph("【参考文献】", styles['Normal']))
                if not st.session_state.references_list.empty:
                    ref_data = [["書籍名・サイト名", "著者・発行者", "発行年・URL"]]
                    ref_dict = st.session_state.references_list.to_dict(orient="records")
                    for item in ref_dict:
                         ref_data.append([
                             item.get("書籍名・サイト名", ""),
                             item.get("著者・発行者", ""),
                             item.get("発行年・URL", "")
                         ])
                    
                    if len(ref_data) > 1:
                        rt = Table(ref_data, colWidths=[60*mm, 50*mm, 50*mm])
                        rt.setStyle(TableStyle([
                            ('FONT', (0,0), (-1,-1), 'IPAexGothic'),
                            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                            ('BACKGROUND', (0,0), (1,0), colors.lightgrey),
                            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                        ]))
                        elements.append(rt)
                    else:
                        elements.append(Paragraph("なし", styles['Normal']))
                else:
                    elements.append(Paragraph("なし", styles['Normal']))

                elements.append(Spacer(1, 4*mm))

                # 2. 実験方法
                elements.append(Paragraph("2. 実験方法", styles['Heading2']))
                elements.append(Paragraph("【使用器具】", styles['Normal']))
                tools_data = [["器具・装置・薬品名", "用途・役割など"]]
                tools_dict = st.session_state.tools_list.to_dict(orient="records")
                for item in tools_dict:
                    # 新旧カラム名の両対応（旧名がある場合はそちらを使用）
                    name = item.get("器具・装置・薬品名", item.get("器具名", ""))
                    role = item.get("用途・役割など", item.get("役割", ""))
                    tools_data.append([name, role])
                
                if len(tools_data) > 1:
                    t = Table(tools_data, colWidths=[60*mm, 100*mm])
                    t.setStyle(TableStyle([
                        ('FONT', (0,0), (-1,-1), 'IPAexGothic'),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                        ('BACKGROUND', (0,0), (1,0), colors.lightgrey),
                        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ]))
                    elements.append(t)
                else:
                    elements.append(Paragraph("なし", styles['Normal']))
                elements.append(Spacer(1, 3*mm))

                if st.session_state.apparatus_photo_data:
                    elements.append(Paragraph("【作成した実験装置】", styles['Normal']))
                    try:
                        img_data = base64.b64decode(st.session_state.apparatus_photo_data)
                        img_io = BytesIO(img_data)
                        img = create_proportional_image(img_io, max_width=120*mm, max_height=80*mm)
                        elements.append(img)
                    except Exception as e:
                        elements.append(Paragraph(f"(画像読み込みエラー: {e})", styles['Normal']))
                    elements.append(Spacer(1, 3*mm))

                elements.append(Paragraph(f"【評価方法】 {st.session_state.evaluation_method}", styles['Normal']))
                elements.append(Spacer(1, 5*mm))

                # 3. 実験結果
                elements.append(Paragraph("3. 実験結果", styles['Heading2']))
                
                if st.session_state.exp_title == "実験① 熱の可視化":
                    # 融解温度テーブル
                    elements.append(Paragraph("■ ロウの融解温度(℃)", styles['Normal']))
                    m_df = st.session_state.melting_point_df
                    m_table_data = [m_df.columns.tolist()] + m_df.values.tolist()
                    mt = Table(m_table_data, colWidths=[30*mm]*4)
                    mt.setStyle(TableStyle([
                        ('FONT', (0,0), (-1,-1), 'IPAexGothic'),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                        ('BACKGROUND', (0,0), (1,0), colors.lightgrey),
                        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ]))
                    elements.append(mt)
                    elements.append(Spacer(1, 3*mm))

                    elements.append(Paragraph("■ 距離と融解時間", styles['Normal']))
                    df = st.session_state.result_df
                    table_data = [df.columns.tolist()] + df.values.tolist()
                    col_w = 40*mm
                    t = Table(table_data, colWidths=[col_w]*len(df.columns))
                    t.setStyle(TableStyle([
                        ('FONT', (0,0), (-1,-1), 'IPAexGothic'),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                        ('BACKGROUND', (0,0), (1,0), colors.lightgrey),
                        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ]))
                    elements.append(t)
                    elements.append(Spacer(1, 2*mm))

                    # 4. 結果グラフ
                    elements.append(Paragraph("4. 結果グラフ", styles['Heading2']))
                    try:
                        fig = create_graph()
                        img_buffer = BytesIO()
                        fig.savefig(img_buffer, format='png', dpi=100)
                        img_buffer.seek(0)
                        img = create_proportional_image(img_buffer, max_width=140*mm, max_height=90*mm)
                        img.hAlign = 'CENTER'
                        elements.append(img)
                        plt.close(fig)
                    except Exception as e:
                        elements.append(Paragraph(f"グラフ作成エラー: {e}", styles['Normal']))
                    
                    caption_style = ParagraphStyle('Caption', parent=styles['Normal'], alignment=TA_CENTER)
                    elements.append(Paragraph("図：熱が伝導した距離とロウの融解時間の関係（溶け始めの時間）", caption_style))
                    elements.append(Spacer(1, 5*mm))

                    # 5. 比較検証・考察
                    elements.append(Paragraph("5. 比較検証・考察", styles['Heading2']))
                    lit_vals = f"熱伝導率の文献値: 銅={st.session_state.lit_cu}, アルミ={st.session_state.lit_al}, ステンレス={st.session_state.lit_sus} (W/m/K)"
                    elements.append(Paragraph(lit_vals, styles['Normal']))
                    elements.append(Spacer(1, 2*mm))
                    elements.append(Paragraph("【考察】", styles['Normal']))
                    elements.append(Paragraph(st.session_state.comparison_text, styles['Normal']))
                    elements.append(Spacer(1, 2*mm))
                    if st.session_state.thermal_conductivity_ref:
                        elements.append(Paragraph(f"（熱伝導率の参考文献: {st.session_state.thermal_conductivity_ref}）", styles['Normal']))

                elif st.session_state.exp_title == "実験② アルカリ型燃料電池の組み立て":
                    # 充電実験
                    elements.append(Paragraph("■ 充電実験", styles['Normal']))
                    c_df = st.session_state.fc_charge_df
                    c_table_data = [c_df.columns.tolist()] + c_df.values.tolist()
                    ct = Table(c_table_data, colWidths=[40*mm]*3)
                    ct.setStyle(TableStyle([
                        ('FONT', (0,0), (-1,-1), 'IPAexGothic'),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                        ('BACKGROUND', (0,0), (1,0), colors.lightgrey),
                        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ]))
                    elements.append(ct)
                    elements.append(Spacer(1, 3*mm))

                    # 放電実験
                    elements.append(Paragraph("■ 放電実験", styles['Normal']))
                    for i, df in enumerate([st.session_state.fc_discharge_1, st.session_state.fc_discharge_2, st.session_state.fc_discharge_3]):
                        elements.append(Paragraph(f"【{i+1}回目】", styles['Normal']))
                        d_table_data = [df.columns.tolist()] + df.values.tolist()
                        dt = Table(d_table_data, colWidths=[25*mm]*5)
                        dt.setStyle(TableStyle([
                            ('FONT', (0,0), (-1,-1), 'IPAexGothic'),
                            ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                            ('BACKGROUND', (0,0), (1,0), colors.lightgrey),
                            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                            ('FONTSIZE', (0,0), (-1,-1), 8),
                        ]))
                        elements.append(dt)
                        elements.append(Spacer(1, 2*mm))

                    # 4. 結果グラフ
                    elements.append(Paragraph("4. 結果グラフ", styles['Heading2']))
                    try:
                        fig = create_fuel_cell_graph()
                        img_buffer = BytesIO()
                        fig.savefig(img_buffer, format='png', dpi=100)
                        img_buffer.seek(0)
                        img = create_proportional_image(img_buffer, max_width=140*mm, max_height=90*mm)
                        img.hAlign = 'CENTER'
                        elements.append(img)
                        plt.close(fig)
                    except Exception as e:
                        elements.append(Paragraph(f"グラフ作成エラー: {e}", styles['Normal']))
                    
                    caption_style = ParagraphStyle('Caption', parent=styles['Normal'], alignment=TA_CENTER)
                    elements.append(Paragraph("図：放電時の時間と出力の関係", caption_style))
                    elements.append(Spacer(1, 5*mm))

                    # 近似仕事量表
                    elements.append(Paragraph("■ 発生エネルギー (J)", styles['Normal']))
                    areas = []
                    for df_raw in [st.session_state.fc_discharge_1, st.session_state.fc_discharge_2, st.session_state.fc_discharge_3]:
                         try:
                             # 念のため DataFrame 変換
                             df = pd.DataFrame(df_raw) if not isinstance(df_raw, pd.DataFrame) else df_raw
                             t = pd.to_numeric(df["放電時間(sec)"], errors="coerce").fillna(0).values
                             p = pd.to_numeric(df["出力(mW)"], errors="coerce").fillna(0).values
                             area_mJ = 0
                             for k in range(len(t)-1):
                                 dt = t[k+1] - t[k]
                                 avg_p = (p[k+1] + p[k]) / 2.0
                                 area_mJ += dt * avg_p
                             areas.append(f"{area_mJ/1000:.2f}")
                         except Exception as e:
                             areas.append("-")
                    
                    area_table_data = [["1回目", "2回目", "3回目"], areas]
                    at = Table(area_table_data, colWidths=[30*mm]*3)
                    at.setStyle(TableStyle([
                        ('FONT', (0,0), (-1,-1), 'IPAexGothic'),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                        ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
                        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ]))
                    elements.append(at)
                    elements.append(Spacer(1, 5*mm))

                    # 5. 比較検証・考察
                    elements.append(Paragraph("5. 比較検証・考察", styles['Heading2']))
                    elements.append(Paragraph("【充電条件の比較と考察】", styles['Normal']))
                    elements.append(Paragraph(st.session_state.fc_comparison_text, styles['Normal']))

                elif st.session_state.exp_title == "実験③ 水処理装置の設計と提案":
                    # 実験結果 - 写真とテキスト
                    elements.append(Paragraph("■ 浄化対象の水", styles['Normal']))
                    if st.session_state.wt_original_water_photo:
                        try:
                            img_data = base64.b64decode(st.session_state.wt_original_water_photo)
                            img = create_proportional_image(BytesIO(img_data), max_width=100*mm, max_height=70*mm)
                            elements.append(img)
                        except: pass
                    elements.append(Spacer(1, 3*mm))

                    elements.append(Paragraph("■ 試作検討①", styles['Heading2']))
                    # 写真並記
                    p1_imgs = []
                    if st.session_state.wt_proto1_dev_photo:
                        try:
                             p1_imgs.append(create_proportional_image(BytesIO(base64.b64decode(st.session_state.wt_proto1_dev_photo)), max_width=75*mm, max_height=55*mm))
                        except: pass
                    if st.session_state.wt_proto1_water_photo:
                        try:
                             p1_imgs.append(create_proportional_image(BytesIO(base64.b64decode(st.session_state.wt_proto1_water_photo)), max_width=75*mm, max_height=55*mm))
                        except: pass
                    
                    if p1_imgs:
                        t_data = [p1_imgs]
                        t = Table(t_data)
                        t.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'TOP')]))
                        elements.append(t)

                    elements.append(Paragraph("【原理や工夫】", styles['Normal']))
                    elements.append(Paragraph(st.session_state.wt_proto1_text, styles['Normal']))
                    elements.append(Spacer(1, 4*mm))

                    elements.append(Paragraph("■ 試作検討②", styles['Heading2']))
                    p2_imgs = []
                    if st.session_state.wt_proto2_dev_photo:
                        try:
                             p2_imgs.append(create_proportional_image(BytesIO(base64.b64decode(st.session_state.wt_proto2_dev_photo)), max_width=75*mm, max_height=55*mm))
                        except: pass
                    if st.session_state.wt_proto2_water_photo:
                        try:
                             p2_imgs.append(create_proportional_image(BytesIO(base64.b64decode(st.session_state.wt_proto2_water_photo)), max_width=75*mm, max_height=55*mm))
                        except: pass
                    
                    if p2_imgs:
                        t_data = [p2_imgs]
                        t = Table(t_data)
                        t.setStyle(TableStyle([('ALIGN', (0,0), (-1,-1), 'CENTER'), ('VALIGN', (0,0), (-1,-1), 'TOP')]))
                        elements.append(t)
                        
                    elements.append(Paragraph("【原理や工夫】", styles['Normal']))
                    elements.append(Paragraph(st.session_state.wt_proto2_text, styles['Normal']))
                    elements.append(Spacer(1, 4*mm))

                    # 清澄度評価
                    elements.append(Paragraph("■ 清澄度評価 (1000点満点)", styles['Heading2']))
                    clarity_df = st.session_state.wt_clarity_df
                    c_table_data = [clarity_df.columns.tolist()] + clarity_df.values.tolist()
                    ct = Table(c_table_data, colWidths=[40*mm]*2)
                    ct.setStyle(TableStyle([
                        ('FONT', (0,0), (-1,-1), 'IPAexGothic'),
                        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                        ('BACKGROUND', (0,0), (1,0), colors.lightgrey),
                        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ]))
                    elements.append(ct)
                    elements.append(Spacer(1, 4*mm))

                    # 凝集剤の効果
                    elements.append(Paragraph("■ 凝集剤の効果", styles['Heading2']))
                    if st.session_state.wt_coagulation_photo:
                        try:
                            img = create_proportional_image(BytesIO(base64.b64decode(st.session_state.wt_coagulation_photo)), max_width=100*mm, max_height=70*mm)
                            elements.append(img)
                        except: pass
                    elements.append(Spacer(1, 2*mm))
                    elements.append(Paragraph("【原理】", styles['Normal']))
                    elements.append(Paragraph(st.session_state.wt_coagulation_text, styles['Normal']))
                    elements.append(Spacer(1, 5*mm))

                    # 5. 比較検証・考察
                    elements.append(Paragraph("5. 比較検証・考察", styles['Heading2']))
                    elements.append(Paragraph("【装置の比較（試作① vs 試作②）】", styles['Normal']))
                    elements.append(Paragraph(st.session_state.wt_comparison_text, styles['Normal']))

                doc.build(elements)
                
                st.session_state["pdf_bytes"] = buffer.getvalue()
                st.success("PDFを作成しました。ダウンロードボタンを押してください。")
            except Exception as e:
                st.error(f"PDF作成エラー: {e}")

        if "pdf_bytes" in st.session_state:
            filename_pdf = f"{st.session_state.student_id}_{st.session_state.student_name}_{st.session_state.exp_title}.pdf".replace(" ", "_").replace("　", "_")
            st.download_button("提出用ファイルのダウンロード", st.session_state["pdf_bytes"], file_name=filename_pdf, mime="application/pdf")

# -----------------------
# 基本情報入力
# -----------------------
with st.expander("基本情報入力", expanded=True):
    # 1段目：実験タイトル、実験日、クラス
    r1_col1, r1_col2, r1_col3 = st.columns([3, 1, 1])
    with r1_col1:
        current_title = st.session_state.exp_title
        selected_title = st.selectbox(
            "実験タイトル",
            list(QUESTION_DICT.keys()),
            index=list(QUESTION_DICT.keys()).index(current_title),
            key="exp_title_selector",
            help="実験のテーマを選択してください"
        )
        if selected_title != current_title:
            confirm_exp_title_change_dialog(selected_title)
    with r1_col2:
        st.date_input("実験日", key="exp_date", help="実験を実施した日付を入力してください")
    with r1_col3:
        st.selectbox(
            "クラス",
            ["1年1組","1年2組","1年3組","1年4組"],
            key="class_name",
            help="所属するクラスを選択してください"
        )
    
    st.divider()
    
    # 2段目：本人の席番号、出席番号、氏名
    r2_col1, r2_col2, r2_col3 = st.columns([1, 1, 3])
    with r2_col1:
        st.text_input("席番号", key="seat_number", help="自分の席番号を入力してください")
    with r2_col2:
        st.text_input("出席番号", key="student_id", help="自分の出席番号を入力してください")
    with r2_col3:
        st.text_input("氏名", key="student_name", help="自分の氏名を入力してください")

    # 3段目：共同実験者①、②
    r3_col1, r3_col2, r3_col3, r3_col4 = st.columns([1, 2, 1, 2])
    with r3_col1:
        st.text_input("共同実験者① 出席番号", key="partner1_id")
    with r3_col2:
        st.text_input("共同実験者① 氏名", key="partner1_name")
    with r3_col3:
        st.text_input("共同実験者② 出席番号", key="partner2_id")
    with r3_col4:
        st.text_input("共同実験者② 氏名", key="partner2_name")

# -----------------------
# 調査レポート（自宅課題）
# -----------------------
with st.expander("🏠 調査レポート（自宅課題）", expanded=True):
    st.info("※ 各設問へは、**指定された必須語句を含めて200文字以上**で記述してください。また、調査に使用した参考文献を下の表にまとめてください。")
    for q, words in QUESTION_DICT[st.session_state.exp_title].items():
        key_name = "設問_" + q.replace("？","").replace(" ","_")
        if key_name not in st.session_state:
            st.session_state[key_name] = ""

        st.text_area(q, height=120, key=key_name, help="この設問について200文字以上で回答を記述してください。調査に使用した文献はページ下部の表に記入してください。")

        if words:
            check_list = []
            for w in words:
                if w in str(st.session_state[key_name]):
                    check_list.append(f":green[✔ {w}]")
                else:
                    check_list.append(f":grey[✖ {w}]")
            st.markdown("**必須語チェック** : " + "  ".join(check_list))
        
        char_count = len(str(st.session_state[key_name]))
        if char_count < 200:
             st.caption(f"文字数：{char_count} / 200文字以上 (:red[あと {200 - char_count} 文字])")
        else:
             st.caption(f"文字数：{char_count} :green[✔ OK]")

    st.divider()
    st.markdown("### 参考文献")
    st.caption("調査に使用した書籍やウェブサイトを入力してください。")
    edited_refs = st.data_editor(
        st.session_state.references_list,
        num_rows="dynamic",
        key="references_list_editor"
    )
    st.session_state["references_list"] = edited_refs

# -----------------------
# 実験方法
# -----------------------
with st.expander("実験方法", expanded=True):
    st.markdown("### 実験で用意したもの（装置・器具・薬品）")
    st.caption("実験で使用した器具や材料を入力してください。行を追加ボタンで増やせます。")

    edited_tools = st.data_editor(
        st.session_state.tools_list,
        num_rows="dynamic",
        key="tools_list_editor"
    )
    st.session_state["tools_list"] = edited_tools

    if st.session_state.exp_title != "実験③ 水処理装置の設計と提案":
        st.markdown("### 作成した実験装置")
        uploaded_camera = st.file_uploader(
            "写真 (jpg, png)", 
            type=["jpg","jpeg","png"], 
            key="apparatus_photo_upload",
            help="組み立てた実験装置の写真を撮影し、アップロードしてください。"
        )
        if uploaded_camera is not None:
             # アップロードされたらsession_stateに保存(base64化)
             bytes_data = uploaded_camera.getvalue()
             st.session_state["apparatus_photo_data"] = base64.b64encode(bytes_data).decode()
        
        # 保存された画像の表示
        if st.session_state["apparatus_photo_data"]:
            st.image(base64.b64decode(st.session_state["apparatus_photo_data"]), use_container_width=True)
            if st.button("装置の写真を削除", key="btn_del_apparatus"):
                st.session_state["apparatus_photo_data"] = None
                if "apparatus_photo_upload" in st.session_state:
                    del st.session_state["apparatus_photo_upload"]
                st.rerun()

    if st.session_state.exp_title != "実験③ 水処理装置の設計と提案":
        st.text_input(
            "評価方法（100字程度）", 
            key="evaluation_method",
            help="どのような基準や方法で結果を測定・判定したか記述してください。"
        )

# -----------------------
# -----------------------
# 実験結果入力
# -----------------------
st.markdown("### 実験結果入力")

if st.session_state.exp_title == "実験① 熱の可視化":
    with st.expander("実験結果（熱の可視化）", expanded=True):
        st.markdown("#### ロウ（流動パラフィン）の融解温度")
        st.caption("前実験での測定値を入力してください。平均は自動計算されます。")
        
        # 融解温度データエディタ
        edited_melting = st.data_editor(
            st.session_state.melting_point_df,
            num_rows="fixed",
            key="melting_point_editor",
            hide_index=True,
            column_config={
                "平均(℃)": st.column_config.TextColumn("平均(℃)", disabled=True)
            }
        )
        
        # 平均値の自動計算
        st.session_state["melting_point_df"] = edited_melting

        try:
            idx_label = edited_melting.index[0]
            vals = []
            for col in ["1回目(℃)", "2回目(℃)", "3回目(℃)"]:
                v = pd.to_numeric(edited_melting.at[idx_label, col], errors="coerce")
                if not pd.isna(v):
                    vals.append(v)
            
            should_rerun = False
            if vals:
                avg_val = round(sum(vals) / len(vals), 1)
                current_avg_num = pd.to_numeric(edited_melting.at[idx_label, "平均(℃)"], errors="coerce")
                if pd.isna(current_avg_num) or avg_val != current_avg_num:
                    edited_melting.at[idx_label, "平均(℃)"] = str(avg_val)
                    st.session_state["melting_point_df"] = edited_melting
                    should_rerun = True
            else:
                if edited_melting.at[idx_label, "平均(℃)"] != "":
                    edited_melting.at[idx_label, "平均(℃)"] = ""
                    st.session_state["melting_point_df"] = edited_melting
                    should_rerun = True
            
            if should_rerun:
                if "melting_point_editor" in st.session_state:
                    del st.session_state["melting_point_editor"]
                st.rerun()
        except Exception as e:
            pass

        st.divider()

        st.markdown("#### 金属棒ごとの融解時間")
        st.caption("※ 距離(cm)は、アルミパイプ、銅パイプ、ステンレスパイプ（SUS304）の加熱端からの距離です。")
        st.caption("各距離におけるロウの融解時間を秒単位で入力してください。")
        edited_df = st.data_editor(
            st.session_state.result_df,
            num_rows="dynamic",
            key="result_df_editor"
        )
        st.session_state["result_df"] = edited_df

elif st.session_state.exp_title == "実験② アルカリ型燃料電池の組み立て":
    with st.expander("実験結果（アルカリ型燃料電池）", expanded=True):
        st.markdown("#### 充電実験")
        st.caption("アルカリ水溶液を電解した際の電解条件（充電条件）を設定し、充電後に開回路電圧(V)を測定してください。")
        st.session_state["fc_charge_df"] = st.data_editor(
            st.session_state.fc_charge_df,
            key="fc_charge_editor"
        )
        
        # 自動計算ロジック
        def update_fc_table(df):
            if not isinstance(df, pd.DataFrame):
                return df
            for i in df.index:
                try:
                    v = pd.to_numeric(df.at[i, "端子電圧(V)"], errors="coerce")
                    a = pd.to_numeric(df.at[i, "電流(mA)"], errors="coerce")
                    if not pd.isna(v) and not pd.isna(a):
                        df.at[i, "出力(mW)"] = str(round(v * a, 2))
                except: pass
            return df

        st.markdown("#### 放電実験 (1回目)")
        st.caption("端子電圧、電流を入力すると、エネルギー（≒出力）が計算されます。")
        edited_d1 = st.data_editor(st.session_state.fc_discharge_1, key="fc_d1_editor")
        st.session_state["fc_discharge_1"] = update_fc_table(edited_d1)

        st.markdown("#### 放電実験 (2回目)")
        edited_d2 = st.data_editor(st.session_state.fc_discharge_2, key="fc_d2_editor")
        st.session_state["fc_discharge_2"] = update_fc_table(edited_d2)

        st.markdown("#### 放電実験 (3回目)")
        edited_d3 = st.data_editor(st.session_state.fc_discharge_3, key="fc_d3_editor")
        st.session_state["fc_discharge_3"] = update_fc_table(edited_d3)

elif st.session_state.exp_title == "実験③ 水処理装置の設計と提案":
    with st.expander("実験結果（水処理装置）", expanded=True):
        # 浄化対象の水
        st.markdown("#### 浄化対象の水")
        u_orig = st.file_uploader("浄化対象の水の写真", type=["jpg","png"], key="u_orig")
        if u_orig:
            st.session_state.wt_original_water_photo = base64.b64encode(u_orig.getvalue()).decode()
        if st.session_state.wt_original_water_photo:
            st.image(base64.b64decode(st.session_state.wt_original_water_photo), use_container_width=True)
            if st.button("浄化前の写真を削除", key="btn_del_wt_orig"):
                st.session_state.wt_original_water_photo = None
                if "u_orig" in st.session_state: del st.session_state["u_orig"]
                st.rerun()
        
        st.divider()
        # 試作検討①
        st.markdown("#### 試作検討①")
        c1, c2 = st.columns(2)
        with c1:
            u_p1_d = st.file_uploader("作成した実験装置の写真 (試作①)", type=["jpg","png"], key="u_p1_d")
            if u_p1_d: st.session_state.wt_proto1_dev_photo = base64.b64encode(u_p1_d.getvalue()).decode()
            if st.session_state.wt_proto1_dev_photo: 
                st.image(base64.b64decode(st.session_state.wt_proto1_dev_photo), use_container_width=True)
                if st.button("装置①を削除", key="btn_del_p1d"):
                    st.session_state.wt_proto1_dev_photo = None
                    if "u_p1_d" in st.session_state: del st.session_state["u_p1_d"]
                    st.rerun()
        with c2:
            u_p1_w = st.file_uploader("浄化後の水の写真 (試作①)", type=["jpg","png"], key="u_p1_w")
            if u_p1_w: st.session_state.wt_proto1_water_photo = base64.b64encode(u_p1_w.getvalue()).decode()
            if st.session_state.wt_proto1_water_photo: 
                st.image(base64.b64decode(st.session_state.wt_proto1_water_photo), use_container_width=True)
                if st.button("水①を削除", key="btn_del_p1w"):
                    st.session_state.wt_proto1_water_photo = None
                    if "u_p1_w" in st.session_state: del st.session_state["u_p1_w"]
                    st.rerun()
        
        st.text_area("原理や工夫（試作①） 100字程度", key="wt_proto1_text")

        st.divider()
        # 試作検討②
        st.markdown("#### 試作検討②")
        c1, c2 = st.columns(2)
        with c1:
            u_p2_d = st.file_uploader("作成した実験装置の写真 (試作②)", type=["jpg","png"], key="u_p2_d")
            if u_p2_d: st.session_state.wt_proto2_dev_photo = base64.b64encode(u_p2_d.getvalue()).decode()
            if st.session_state.wt_proto2_dev_photo: 
                st.image(base64.b64decode(st.session_state.wt_proto2_dev_photo), use_container_width=True)
                if st.button("装置②を削除", key="btn_del_p2d"):
                    st.session_state.wt_proto2_dev_photo = None
                    if "u_p2_d" in st.session_state: del st.session_state["u_p2_d"]
                    st.rerun()
        with c2:
            u_p2_w = st.file_uploader("浄化後の水の写真 (試作②)", type=["jpg","png"], key="u_p2_w")
            if u_p2_w: st.session_state.wt_proto2_water_photo = base64.b64encode(u_p2_w.getvalue()).decode()
            if st.session_state.wt_proto2_water_photo: 
                st.image(base64.b64decode(st.session_state.wt_proto2_water_photo), use_container_width=True)
                if st.button("水②を削除", key="btn_del_p2w"):
                    st.session_state.wt_proto2_water_photo = None
                    if "u_p2_w" in st.session_state: del st.session_state["u_p2_w"]
                    st.rerun()

        st.text_area("原理や工夫（試作②） 100字程度", key="wt_proto2_text")

        st.divider()
        # 清澄度評価
        st.markdown("#### 清澄度評価 (1000点満点)")
        st.session_state.wt_clarity_df = st.data_editor(st.session_state.wt_clarity_df, key="wt_clarity_editor")

        st.divider()
        # 凝集剤の効果
        st.markdown("#### 凝集剤の効果")
        u_coag = st.file_uploader("凝集処理後の水の写真をアップロード", type=["jpg","png"], key="u_coag")
        if u_coag: st.session_state.wt_coagulation_photo = base64.b64encode(u_coag.getvalue()).decode()
        if st.session_state.wt_coagulation_photo: 
            st.image(base64.b64decode(st.session_state.wt_coagulation_photo), use_container_width=True)
            if st.button("凝集後の写真を削除", key="btn_del_coag"):
                st.session_state.wt_coagulation_photo = None
                if "u_coag" in st.session_state: del st.session_state["u_coag"]
                st.rerun()
        
        st.text_area("原理（凝集剤） 100字程度", key="wt_coagulation_text")

# -----------------------
# 比較検証・考察
# -----------------------
with st.expander("比較検証と考察", expanded=True):
    if st.session_state.exp_title == "実験① 熱の可視化":
        col1, col2, col3 = st.columns(3)
        with col1:
            st.text_input("銅の熱伝導率 W/m/K", key="lit_cu", help="銅の熱伝導率を調べて入力してください。")
        with col2:
            st.text_input("アルミの熱伝導率 W/m/K", key="lit_al", help="アルミの熱伝導率を調べて入力してください。")
        with col3:
            st.text_input("ステンレス(SUS304)の熱伝導率 W/m/K", key="lit_sus", help="ステンレス(SUS304等)の熱伝導率を調べて入力してください。")

        st.text_area(
            "実験結果との比較（100字程度）", 
            key="comparison_text", 
            height=80,
            help="グラフの傾きや順序が文献値の傾向と一致しているか、材質の違いがどう影響したか等を考察してください。"
        )
        st.text_input("熱伝導率の引用文献 (1件)", key="thermal_conductivity_ref")

    elif st.session_state.exp_title == "実験② アルカリ型燃料電池の組み立て":
        st.text_area(
            "充電条件の比較（100字程度）",
            key="fc_comparison_text",
            height=100,
            help="充電時間や電圧の違いが放電特性（グラフの形や持続時間）にどう影響したか考察してください。"
        )
    elif st.session_state.exp_title == "実験③ 水処理装置の設計と提案":
        st.text_area(
            "装置の比較　試作①vs試作②（100字程度）",
            key="wt_comparison_text",
            height=100,
            help="何を変えて、効果はどの程度あったかを記述してください。"
        )

# -----------------------
# 結果グラフ
# -----------------------
with st.expander("結果グラフ", expanded=True):
    if st.session_state.exp_title == "実験① 熱の可視化":
        _, col_center, _ = st.columns([1, 4, 1])
        with col_center:
            fig = create_graph()
            st.pyplot(fig)
            st.markdown("<div style='text-align: center;'>熱が伝導した距離とロウの融解時間の関係（溶け始めの時間）</div>", unsafe_allow_html=True)
            
    elif st.session_state.exp_title == "実験② アルカリ型燃料電池の組み立て":
        _, col_center, _ = st.columns([1, 4, 1])
        with col_center:
            fig = create_fuel_cell_graph()
            st.pyplot(fig)
            st.markdown("<div style='text-align: center;'>放電時の時間と出力の関係（1～3回目）</div>", unsafe_allow_html=True)
        
        st.markdown("#### まとめ表（グラフの折れ線近似で下部面積 ＝ 発生エネルギーJ）")
        areas = []
        for df in [st.session_state.fc_discharge_1, st.session_state.fc_discharge_2, st.session_state.fc_discharge_3]:
             try:
                 t = pd.to_numeric(df["放電時間(sec)"], errors="coerce").fillna(0).values
                 p = pd.to_numeric(df["出力(mW)"], errors="coerce").fillna(0).values
                 
                 area_mJ = 0
                 for i in range(len(t)-1):
                     dt = t[i+1] - t[i]
                     avg_p = (p[i+1] + p[i]) / 2.0
                     area_mJ += dt * avg_p
                 
                 areas.append(f"{area_mJ/1000:.2f}")
             except:
                 areas.append("-")
        
        st.write(pd.DataFrame([areas], columns=["1回目(J)", "2回目(J)", "3回目(J)"], index=["発生エネルギー"]))

    elif st.session_state.exp_title == "実験③ 水処理装置の設計と提案":
        st.info("グラフはありません")




# -----------------------
# ルーブリック（評価基準）
# -----------------------
with st.expander("簡易自己評価（達成度）", expanded=False):
    st.markdown("### 必要条件の達成度")
    st.caption("現在の入力状況に基づく目安の達成度です（最大：100%）。提出前の確認に使ってください。")

    # --- 採点ロジック ---
    score_home, score_report, total, is_default_basic = calculate_achievement_rate()

    # 表示
    c1, c2, c3 = st.columns(3)
    c1.metric("総合達成度", f"{total} %")
    c2.metric("自宅課題", f"{score_home} % (max 50)")
    c3.metric("レポート作成", f"{score_report} % (max 50)")
    
    if total < 60:
        st.error("入力が不足しています。各項目を見直してください。")
    elif total < 80:
        st.warning("合格圏内ですが、さらに記述を充実させましょう。")
    else:
        st.success("素晴らしい出来栄えです！")

    if is_default_basic:

        st.warning("⚠️ 学籍番号や氏名が初期値（例：高専 太郎）のままです。修正してください。")



