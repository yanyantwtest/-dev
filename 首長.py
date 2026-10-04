import hashlib
import os
import requests
import streamlit as st

# 設定網頁標題與圖示
st.set_page_config(
    page_title="人事部勞工運行狀態中心", page_icon="📊", layout="centered"
)

# ------------------------------------------------------------------------------
# 隱藏 Streamlit 右上角選單 (Share, Star, GitHub, 選單) 與 頁尾
# ------------------------------------------------------------------------------
hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}
    .stAppHeader {display: none;}
    </style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)


# ==============================================================================
# 【區塊 1】DISCORD API 模組
# ==============================================================================
class DiscordAPI:

  @staticmethod
  def send_message(bot_token: str, channel_id: str, message_text: str):
    """發送訊息至 Discord 頻道"""
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
    headers = {
        "Authorization": f"Bot {bot_token.strip()}",
        "Content-Type": "application/json",
    }
    try:
      response = requests.post(
          url, json={"content": message_text}, headers=headers, timeout=10
      )
      if response.status_code in [200, 201]:
        msg_id = response.json().get("id", "無紀錄")
        return True, f"訊息已成功發送！ (訊息 ID: `{msg_id}`)"
      error_msg = response.json().get("message", "未知錯誤")
      return False, f"發送失敗 (HTTP {response.status_code}): {error_msg}"
    except Exception as e:
      return False, f"連線異常：{str(e)}"

  @staticmethod
  def delete_message(bot_token: str, channel_id: str, message_id: str):
    """刪除指定 Discord 訊息"""
    url = f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id.strip()}"
    headers = {"Authorization": f"Bot {bot_token.strip()}"}
    try:
      response = requests.delete(url, headers=headers, timeout=10)
      if response.status_code == 204:
        return True, f"訊息 ID `{message_id}` 已成功刪除！"
      elif response.status_code == 404:
        return False, "刪除失敗：找不到該訊息或已被刪除。"
      elif response.status_code == 403:
        return False, "刪除失敗：Bot 缺少『管理訊息 (Manage Messages)』權限。"
      error_msg = response.json().get("message", "未知錯誤")
      return False, f"刪除失敗 (HTTP {response.status_code}): {error_msg}"
    except Exception as e:
      return False, f"連線異常：{str(e)}"


# ==============================================================================
# 【區塊 2】全域共享狀態管理 (快取核心)
# ==============================================================================
class StatusManagerV3:

  def __init__(self):
    self.current_status = "🟢 上線"
    self.notice_message = ""
    self.ticker_text = (
        "🎉 歡迎來到人事部勞工運行狀態中心！系統目前正常運作中。"
    )
    self.logs = []
    self.add_log("🟢 上線", "系統初始化")

  def set_status(self, new_status, notice="", ticker=""):
    self.current_status = new_status
    self.notice_message = notice
    self.ticker_text = ticker[:60] if ticker else ""
    self.add_log(new_status, notice)

  def get_status_info(self):
    return {
        "status": self.current_status,
        "notice": self.notice_message,
        "ticker": self.ticker_text,
    }

  def add_log(self, status, notice):
    self.logs.insert(
        0, {"status": status, "notice": notice if notice else "無補充說明"}
    )
    if len(self.logs) > 20:
      self.logs.pop()

  def get_logs(self):
    return self.logs


@st.cache_resource
def get_status_manager():
  return StatusManagerV3()


status_manager = get_status_manager()


# ==============================================================================
# 【區塊 3】安全驗證與登入狀態
# ==============================================================================
def check_password(password_input):
  secret_password = st.secrets.get(
      "ADMIN_PASSWORD", os.environ.get("ADMIN_PASSWORD", "admin")
  )
  hash_input = hashlib.sha256(password_input.encode()).hexdigest()
  hash_secret = hashlib.sha256(secret_password.encode()).hexdigest()
  return hash_input == hash_secret


if "logged_in" not in st.session_state:
  st.session_state["logged_in"] = False


# ==============================================================================
# 【區塊 4】前台展示區 (一般使用者看到的畫面)
# ==============================================================================
st.title("🌐 BOT運行狀態")


@st.fragment(run_every=5)
def render_status_display():
  info = status_manager.get_status_info()
  current_status, notice, ticker = (
      info["status"],
      info["notice"],
      info["ticker"],
  )

  # 跑馬燈元件
  if ticker:
    st.markdown(
        f"""
            <style>
            .ticker-box {{
                width: 100%; background: rgba(255, 255, 255, 0.08);
                border: 1px solid rgba(255, 255, 255, 0.15);
                border-left: 5px solid #ff4b4b; border-radius: 8px;
                padding: 12px 0; margin-bottom: 20px;
                overflow: hidden; position: relative;
            }}
            .ticker-text {{
                display: inline-block; white-space: nowrap;
                animation: marquee 16s linear infinite;
                font-size: 15px; font-weight: 600; line-height: 1.5;
            }}
            @keyframes marquee {{
                0%   {{ transform: translateX(100%); }}
                100% {{ transform: translateX(-100%); }}
            }}
            </style>
            <div class="ticker-box">
                <div class="ticker-text">📢 {ticker}</div>
            </div>
            """,
        unsafe_allow_html=True,
    )

  st.subheader("目前服務狀態")

  if current_status == "🟢 上線":
    st.success(
        "### 🟢 系統正常運行中 (Online)\n目前所有服務皆可正常存取。"
    )
  elif current_status == "🟡 維修中":
    st.warning(
        "### 🟡 系統定期維修中 (Maintenance)\n正在進行例行維護以提升服務品質，造成不便請見諒。"
    )
  elif current_status == "🔴 故障":
    st.error(
        "### 🔴 系統突發故障 (Down)\n服務目前遭遇異常，工程師已收到通知並正搶修中。"
    )

  if notice:
    st.info(f"📌 **詳細說明：** {notice}")

  st.caption("🔄 狀態每 5 秒自動同步更新中...")


render_status_display()
st.divider()


# ==============================================================================
# 【區塊 5】後台介面分頁元件
# ==============================================================================
def render_tab_status():
  """分頁 1：網站狀態與跑馬燈管理"""
  current_info = status_manager.get_status_info()
  status_options = ["🟢 上線", "🟡 維修中", "🔴 故障"]
  current_index = status_options.index(current_info["status"])

  with st.form("update_status_form"):
    new_status = st.radio(
        "請選擇欲變更的網站狀態：",
        options=status_options,
        index=current_index,
    )
    ticker_input = st.text_input(
        "跑馬燈公告內容（上限 60 字，留空則隱藏）：",
        value=current_info["ticker"],
        max_chars=60,
    )
    notice_input = st.text_area(
        "自訂補充公告 / 預計恢復時間（可留空）：",
        value=current_info["notice"],
    )

    if st.form_submit_button("更新設定", type="primary"):
      status_manager.set_status(new_status, notice_input, ticker_input)
      st.success("網站設定已成功更新！")
      st.rerun()


def render_tab_discord():
  """分頁 2：Discord Bot 訊息管理"""
  st.markdown("#### ⚙️ Discord 連線設定")

  # 從 secrets 或環境變數讀取預設值
  default_token = st.secrets.get(
      "DISCORD_BOT_TOKEN", os.environ.get("DISCORD_BOT_TOKEN", "")
  )
  default_channel_id = st.secrets.get(
      "DISCORD_CHANNEL_ID", os.environ.get("DISCORD_CHANNEL_ID", "")
  )

  # 如果 Session State 內沒有紀錄，就帶入從系統讀到的預設值
  token_val = st.session_state.get("dc_bot_token", default_token)
  channel_val = st.session_state.get("dc_channel_id", default_channel_id)

  dc_bot_token = st.text_input(
      "Discord Bot Token：",
      value=token_val,
      type="password",
  )
  dc_channel_id = st.text_input(
      "目標頻道 ID (Channel ID)：",
      value=channel_val,
      placeholder="例如：123456789012345678",
  )

  # 保持 Session 狀態
  st.session_state["dc_bot_token"] = dc_bot_token
  st.session_state["dc_channel_id"] = dc_channel_id

  st.markdown("---")

  # --- 子功能 A：發送訊息 ---
  st.markdown("#### 💬 發送廣播訊息")
  with st.form("discord_message_form"):
    dc_message = st.text_area(
        "發送內容：", placeholder="請輸入要讓機器人發送的公告文字..."
    )
    if st.form_submit_button("🚀 發送訊息", type="primary"):
      if not dc_bot_token or not dc_channel_id:
        st.error("請先填寫 Token 與頻道 ID！")
      elif not dc_message.strip():
        st.warning("訊息內容不可空白！")
      else:
        ok, msg = DiscordAPI.send_message(
            dc_bot_token, dc_channel_id, dc_message
        )
        if ok:
          st.success(msg)
        else:
          st.error(msg)

  st.markdown("---")

  # --- 子功能 B：刪除訊息 ---
  st.markdown("#### 🗑️ 刪除指定訊息")
  with st.form("discord_delete_form"):
    delete_msg_id = st.text_input(
        "要刪除的訊息 ID：", placeholder="例如：1234567890123456789"
    )
    if st.form_submit_button("🗑️ 刪除訊息"):
      if not dc_bot_token or not dc_channel_id:
        st.error("請先填寫 Token 與頻道 ID！")
      elif not delete_msg_id.strip():
        st.warning("請輸入欲刪除的訊息 ID！")
      else:
        ok, msg = DiscordAPI.delete_message(
            dc_bot_token, dc_channel_id, delete_msg_id
        )
        if ok:
          st.success(msg)
        else:
          st.error(msg)


# ==============================================================================
# 【區塊 6】後台主流程 (登入控制與頁面進入點)
# ==============================================================================
st.subheader("🔒 管理員控制台")

if not st.session_state["logged_in"]:
  with st.form("login_form"):
    password_input = st.text_input("請輸入管理員密碼：", type="password")
    if st.form_submit_button("登入後台"):
      if check_password(password_input):
        st.session_state["logged_in"] = True
        st.success("登入成功！")
        st.rerun()
      else:
        st.error("密碼錯誤，請再試一次。")
else:
  st.info("🔓 您已成功登入管理後台。")

  # 後台頁籤路由
  tab1, tab2 = st.tabs(["📊 網站狀態與跑馬燈", "🤖 Discord Bot 管理"])
  with tab1:
    render_tab_status()
  with tab2:
    render_tab_discord()

  # 底部歷史紀錄與登出按鈕
  st.markdown("---")
  with st.expander("📜 查看狀態變更歷史紀錄"):
    st.table(status_manager.get_logs())

  if st.button("登出後台"):
    st.session_state["logged_in"] = False
    st.success("已成功登出。")
    st.rerun()