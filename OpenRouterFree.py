#!/usr/bin/env python3
"""
Enterprise-grade Chat UI for OpenRouter's Cypher Alpha model using Tkinter.

Features:
- Full conversation history with scrollback
- Dark/light theming toggle
- Syntax-highlighted code blocks with copy-on-right-click
- Streaming AI responses in background thread
- Export/import chat history as JSON
- Production/development mode with environment-based API key management
- Startup self-tests to ensure no regression of core functionality
- Multi-line input box for natural typing (Ctrl+Enter to send)
- Granular status updates at every stage
- Inline copy-icon buttons for each message
- Selectable model list with automatic, intelligent fallback
- Debug menu to test all models and refresh list from API.
"""

from dotenv import load_dotenv
import os

load_dotenv()  # Load .env file

import re
import json
import queue
import threading
import requests
import tkinter as tk
from tkinter import scrolledtext, filedialog, messagebox, Menu, PhotoImage
from pygments import lex
from pygments.lexers import get_lexer_by_name
from pygments.token import Token

import base64
from PIL import Image, ImageTk
import io
import cairosvg

try:
    import pyperclip
except ImportError:
    pyperclip = None

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
except ImportError:
    print("FATAL ERROR: tkinterdnd2 library not found.")
    print("Please install it to enable drag-and-drop functionality: pip install tkinterdnd2")
    exit(1)


# ----------------------------------------
# Environment & Mode Configuration
# ----------------------------------------
PRODUCTION = False # os.environ.get("ENV", "development").lower() == "production"

if PRODUCTION:
    try:
        API_KEY = os.environ["OPENROUTER_API_KEY"]
    except KeyError:
        print("Error: OPENROUTER_API_KEY not set. Exiting.")
        exit(1)
else:
    API_KEY = os.environ.get("OPENROUTER_KEY")
#print(API_KEY)

API_URL = "https://openrouter.ai/api/v1/chat/completions"

# ----------------------------------------
# Model Definitions
# ----------------------------------------
AVAILABLE_MODELS = [
    {"display": "Cypher Alpha", "api": "openrouter/cypher-alpha:free"},
    {"display": "Mistral Small 3.2 24B", "api": "mistralai/mistral-small-3.2-24b-instruct:free"},
    {"display": "Kimi Dev 72b", "api": "moonshotai/kimi-dev-72b:free"},
    {"display": "DeepSeek R1 0528 Qwen3 8B", "api": "deepseek/deepseek-r1-0528-qwen3-8b:free"},
    {"display": "DeepSeek R1 0528", "api": "deepseek/deepseek-r1-0528:free"},
    {"display": "Sarvam-M", "api": "sarvamai/sarvam-m:free"},
    {"display": "Devstral Small", "api": "mistralai/devstral-small:free"},
    {"display": "Qwen3 30B A3B", "api": "qwen/qwen3-30b-a3b:free"},
    {"display": "Qwen3 8B", "api": "qwen/qwen3-8b:free"},
    {"display": "Qwen3 14B", "api": "qwen/qwen3-14b:free"},
    {"display": "Qwen3 32B", "api": "qwen/qwen3-32b:free"},
    {"display": "Qwen3 235B A22B", "api": "qwen/qwen3-235b-a22b:free"},
    {"display": "DeepSeek R1T Chimera", "api": "tngtech/deepseek-r1t-chimera:free"},
    {"display": "GLM-Z1-32B-0414", "api": "thudm/glm-z1-32b:free"},
    {"display": "GLM-4-32B-0414", "api": "thudm/glm-4-32b:free"},
    {"display": "DeepCoder-14B-Preview", "api": "agentica-org/deepcoder-14b-preview:free"},
    {"display": "Kimi-VL-A3B-Thinking", "api": "moonshotai/kimi-vl-a3b-thinking:free"},
    {"display": "Llama 3.3 Nemotron Super 49B v1", "api": "nvidia/llama-3.3-nemotron-super-49b-v1:free"},
    {"display": "Qwen2.5 VL 32B Instruct", "api": "qwen/qwen2.5-vl-32b-instruct:free"},
    {"display": "Qwerky 72B", "api": "featherless/qwerky-72b:free"},
    {"display": "Mistral Small 3.1 24B", "api": "mistralai/mistral-small-3.1-24b-instruct:free"},
    {"display": "Llama 3.3 70B Instruct", "api": "meta-llama/llama-3.3-70b-instruct:free"},
    {"display": "Qwen2.5 Coder 32B Instruct", "api": "qwen/qwen2.5-coder-32b-instruct:free"},
    {"display": "Llama 3.2 11B Vision Instruct", "api": "meta-llama/llama-3.2-11b-vision-instruct:free"},
    {"display": "Qwen2.5 72B Instruct", "api": "qwen/qwen2.5-72b-instruct:free"},
    {"display": "Mistral Nemo", "api": "mistralai/mistral-nemo:free"},
    {"display": "Gemma 2 9B", "api": "google/gemma-2-9b:free"},
    {"display": "Mistral 7B Instruct", "api": "mistralai/mistral-7b-instruct:free"}
]

VISION_MODELS = {
    "moonshotai/kimi-vl-a3b-thinking:free",
    "qwen/qwen2.5-vl-32b-instruct:free",
    "meta-llama/llama-3.2-11b-vision-instruct:free",
}

# ----------------------------------------
# UI Theming Definitions
# ----------------------------------------
THEMES = {
    "dark": {
        "bg": "#2b2b2b", "fg": "#dcdcdc", "input_bg": "#3c3f41",
        "btn_bg": "#4a4d4f", "btn_fg": "#dcdcdc",
        "user_fg": "#87ceeb", "ai_fg": "#98fb98",
        "menu_bg": "#2b2b2b", "menu_fg": "#dcdcdc",
        "status_fg": "#a9a9a9", "system_fg": "#ff6347",
        "vision_fg_ok": "#32CD32", "vision_fg_no": "#FF6347"
    },
    "light": {
        "bg": "#ffffff", "fg": "#000000", "input_bg": "#f0f0f0",
        "btn_bg": "#e1e1e1", "btn_fg": "#000000",
        "user_fg": "#00008b", "ai_fg": "#006400",
        "menu_bg": "#ffffff", "menu_fg": "#000000",
        "status_fg": "#555555", "system_fg": "#dc143c",
        "vision_fg_ok": "#228B22", "vision_fg_no": "#B22222"
    }
}

# ----------------------------------------
# Core Chat API Function
# ----------------------------------------
def chat_with_cypher_alpha(messages, model_name, timeout=30):
    """
    Streamed chat completion generator. Yields content chunks or structured errors.
    """
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    payload = {"model": model_name, "messages": messages, "stream": True}
    try:
        with requests.post(API_URL, json=payload, headers=headers, stream=True, timeout=timeout) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line.startswith(b"data: "): continue
                data = line[6:].strip()
                if data == b"[DONE]": break
                try:
                    chunk = json.loads(data)
                    delta = chunk["choices"][0]["delta"]
                    if "content" in delta and delta["content"] is not None:
                        yield delta["content"]
                except (json.JSONDecodeError, KeyError, IndexError):
                    yield {"type": "error", "subtype": "parse", "message": f"Invalid data from {model_name}: {data.decode('utf-8', 'ignore')}"}
                    continue
            yield None
    except requests.exceptions.Timeout:
        yield {"type": "error", "subtype": "network", "message": f"Request timed out for {model_name}."}
        yield None
    except requests.HTTPError as e:
        if e.response.status_code == 401:
            yield {"type": "error", "subtype": "auth_error", "message": "Authentication failed. The API key is invalid or has been revoked."}
        elif e.response.status_code == 429:
            yield {"type": "error", "subtype": "rate_limit", "message": "Rate limit reached. Please wait.", "cooldown": 20}
        elif "not found" in e.response.text.lower() or e.response.status_code == 404:
            yield {"type": "error", "subtype": "model_not_found", "message": f"Model not found: {model_name}"}
        else:
            details = f"Server error {e.response.status_code} on {model_name}."
            try:
                msg = e.response.json().get("error", {}).get("message", e.response.text)
                details += f" Details: {msg}"
            except: pass
            yield {"type": "error", "subtype": "http", "message": details}
        yield None
    except requests.RequestException as e:
        yield {"type": "error", "subtype": "network", "message": str(e)}
        yield None

# ----------------------------------------
# Chat UI Class Definition
# ----------------------------------------
class ChatUI:
    def __init__(self, root):
        self.root = root 
        self.root.title("Cypher Alpha Chat")
        self.root.geometry("900x800")

        self.current_theme = "dark"
        self.messages = []
        self.stream_queue = queue.Queue()
        self.current_stream_content = []
        self.is_streaming = False
        
        self.available_models = AVAILABLE_MODELS[:]
        self.staged_images = []
        
        self.model_var = tk.StringVar(self.root)
        if self.available_models:
            self.model_var.set(self.available_models[0]["display"])
        
        svg_base64 = ("PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMjAwIiB2aWV3Qm94PSIwIDAgMjQgMjQiPgogIDxwYXRoIGZpbGw9ImN1cnJlbnRDb2xvciIgZD0iTTIwIDJIMTBjLTEuMTAzIDAtMiAuODk3LTIgMnY0SDRjLTEuMTAzIDAtMiAuODk3LTIgMnYxMGMwIDEuMTAzLjg5NyAyIDIgMmgxMGMxLjEwMyAwIDItLjg5NyAyLTJ2LTRoNGMxLjEwMyAwIDItLjg5NyAyLTJWNGMwLTEuMTAzLS44OTctMi0yLTJ6TTQgMjBWMTBoMTBsLjAwMiAxMEg0em0xNi02aC00di00YzAtMS4xMDMtLjg5Ny0yLTItMmgtNFY0aDEwdjEweiIvPgo8L3N2Zz4=")
        png_bytes = cairosvg.svg2png(bytestring=base64.b64decode(svg_base64), output_width=16, output_height=16)
        self.copy_icon = PhotoImage(data=base64.b64encode(png_bytes).decode('ascii'))
        
        if not pyperclip:
            print("---")
            print("WARNING: 'pyperclip' library not found. Clipboard functions may not work reliably.")
            print("         Please install it for a better experience: pip install pyperclip")
            print("---")

        self._create_widgets()
        self.apply_theme()
        
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self.handle_drop)

        greeting = "Hello! How can I help you today? Drag and drop images to chat with vision models."
        self.display_message("assistant", greeting, highlight=False)
        self.messages.append({"role": "assistant", "content": greeting})

    def _create_widgets(self):
        """Create menus, chat area, input box, buttons, status bar."""
        self.menu_bar = Menu(self.root)
        self.root.config(menu=self.menu_bar)
        file_menu = Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="New Chat", command=self.new_chat)
        file_menu.add_command(label="Save Chat...", command=self.export_chat)
        file_menu.add_command(label="Load Chat...", command=self.import_chat)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        self.menu_bar.add_cascade(label="File", menu=file_menu)
        view_menu = Menu(self.menu_bar, tearoff=0)
        view_menu.add_command(label="Toggle Theme", command=self.toggle_theme)
        self.menu_bar.add_cascade(label="View", menu=view_menu)

        debug_menu = Menu(self.menu_bar, tearoff=0)
        debug_menu.add_command(label="Test All Models", command=self.start_model_test)
        debug_menu.add_command(label="Refresh Models from API", command=self.start_model_fetch)
        self.menu_bar.add_cascade(label="Debug", menu=debug_menu)

        model_frame = tk.Frame(self.root)
        model_frame.pack(padx=10, pady=(10, 0), fill=tk.X)
        model_label = tk.Label(model_frame, text="Model:")
        model_label.pack(side=tk.LEFT, padx=(0, 5))
        model_names = [m["display"] for m in self.available_models]
        self.model_menu = tk.OptionMenu(model_frame, self.model_var, *model_names if model_names else ["No models available"])
        self.model_menu.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.vision_status_label = tk.Label(model_frame, text="", font=("Segoe UI", 9, "italic"))
        self.vision_status_label.pack(side=tk.LEFT, padx=(10, 0))
        self.model_var.trace_add("write", self.update_vision_status)
        self.update_vision_status()

        self.chat_history = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, state=tk.DISABLED, font=("Segoe UI", 11), relief=tk.FLAT)
        self.chat_history.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)
        self._configure_tags()
        
        self.chat_history.bind("<Button-3>", self.handle_right_click)

        self.staging_area = tk.Frame(self.root)
        self.staging_area.pack(padx=10, pady=5, fill=tk.X)

        input_frame = tk.Frame(self.root)
        input_frame.pack(padx=10, pady=(0, 10), fill=tk.X)
        self.input_text = tk.Text(input_frame, height=4, font=("Segoe UI", 11), relief=tk.FLAT, undo=True)
        self.input_text.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 10))
        self.input_text.bind("<Control-Return>", self.send_message)
        self.send_button = tk.Button(input_frame, text="Send", command=self.send_message, relief=tk.FLAT, borderwidth=2)
        self.send_button.pack(side=tk.RIGHT)

        self.status_bar = tk.Label(self.root, text="Ready (Ctrl+Enter to send)", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def _configure_tags(self):
        self.chat_history.tag_configure("user", justify="left", spacing3=10, lmargin1=10, rmargin=80)
        self.chat_history.tag_configure("assistant", justify="left", spacing3=10, lmargin1=10, rmargin=10)
        self.chat_history.tag_configure("system_warning", font=("Segoe UI", 10, "italic"))
        self.chat_history.tag_configure("code_block", font=("Consolas", 10), lmargin1=20, lmargin2=20, rmargin=20, spacing1=5, spacing3=5, relief=tk.RAISED, borderwidth=1)
        for tok, color in {"Token.Keyword":"#CC7832", "Token.Name.Function":"#FFC66D", "Token.Literal.String.Single":"#A5C261", "Token.Literal.String.Double":"#A5C261", "Token.Comment.Single":"#808080", "Token.Operator":"#DA70D6", "Token.Number.Integer":"#6897BB", "Token.Punctuation": "#dcdcdc", "Token.Name.Builtin": "#93C763", "Token.Name.Class": "#DA70D6"}.items():
            self.chat_history.tag_configure(tok.replace(".", "_"), foreground=color)

    def apply_theme(self):
        t = THEMES[self.current_theme]
        self.root.config(bg=t["bg"])
        self.chat_history.config(bg=t["bg"], fg=t["fg"], insertbackground=t["fg"])
        self.input_text.config(bg=t["input_bg"], fg=t["fg"], insertbackground=t["fg"])
        self.send_button.config(bg=t["btn_bg"], fg=t["btn_fg"], activebackground=t["input_bg"], activeforeground=t["btn_fg"])
        self.status_bar.config(bg=t["bg"], fg=t["status_fg"])
        self.menu_bar.config(bg=t["menu_bg"], fg=t["menu_fg"], activebackground=t["input_bg"], activeforeground=t["btn_fg"])
        self.staging_area.config(bg=t["bg"])
        for widget in self.root.winfo_children():
            if isinstance(widget, tk.Frame) and any(isinstance(child, tk.OptionMenu) for child in widget.winfo_children()):
                widget.config(bg=t["bg"])
                for child in widget.winfo_children():
                    if isinstance(child, tk.Label): child.config(bg=t["bg"], fg=t["fg"])
                    elif isinstance(child, tk.OptionMenu):
                        child.config(bg=t["btn_bg"], fg=t["btn_fg"], activebackground=t["input_bg"], activeforeground=t["btn_fg"], highlightthickness=0)
                        child["menu"].config(bg=t["menu_bg"], fg=t["menu_fg"])
        self.chat_history.tag_configure("user", foreground=t["user_fg"])
        self.chat_history.tag_configure("assistant", foreground=t["ai_fg"])
        self.chat_history.tag_configure("system_warning", foreground=t["system_fg"])
        self.chat_history.tag_configure("code_block", background=t["input_bg"], foreground=t["fg"])
        self.update_vision_status()

    def display_message(self, role, content, highlight=True, model_name=None):
        self.chat_history.config(state=tk.NORMAL)
        if role == "user": label = "You"
        elif role == "assistant": label = model_name or "Assistant"
        else: label = "System"
        
        text_content = ""
        image_list = []

        if isinstance(content, list):
            for part in content:
                if part["type"] == "text":
                    text_content += part["text"]
                elif part["type"] == "image_url":
                    image_list.append(part["image_url"]["url"])
            content_body = text_content.strip()
        else:
            content_body = content.strip()

        self.chat_history.insert(tk.END, f"{label}\n", (role,))
        content_start_index = self.chat_history.index(tk.END)
        self.chat_history.insert(tk.END, content_body)

        if image_list:
            self.chat_history.insert(tk.END, " ")
            self.chat_history.insert(tk.END, f"[{len(image_list)} image(s)]", "system_warning")

        content_end_index = self.chat_history.index("end-1c")
        
        if role in ["user", "assistant"]:
            self._add_copy_button(content_end_index, content_body)
        
        self.chat_history.insert(tk.END, "\n\n")

        if role=="assistant" and highlight:
            self._highlight_code_in_range(content_start_index, content_end_index)
            
        self.chat_history.config(state=tk.DISABLED)
        self.chat_history.see(tk.END)

    def _add_copy_button(self, insert_pos, content_to_copy):
        theme = THEMES[self.current_theme]
        copy_btn = tk.Button(self.chat_history, image=self.copy_icon, command=lambda c=content_to_copy: self.copy_message_content(c), relief=tk.FLAT, borderwidth=0, cursor="hand2", bg=theme["bg"], activebackground=theme["input_bg"])
        self.chat_history.window_create(insert_pos, window=copy_btn, padx=5, align="top")

    def copy_message_content(self, content):
        if not content:
            self.status_bar.config(text="Nothing to copy.")
            self.root.after(2000, lambda: self.status_bar.config(text="Ready (Ctrl+Enter to send)"))
            return
        if pyperclip:
            try:
                pyperclip.copy(content)
                self.status_bar.config(text="Copied to clipboard!")
            except Exception as e:
                self.status_bar.config(text=f"Clipboard error: {e}")
        else:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            self.root.update()
            self.status_bar.config(text="Copied (fallback). Paste may not work.")
        self.root.after(2500, lambda: self.status_bar.config(text="Ready (Ctrl+Enter to send)"))

    def _highlight_code_in_range(self, start, end):
        seg = self.chat_history.get(start, end)
        for m in re.finditer(r"```(\w+)?\n(.*?)```", seg, re.DOTALL):
            bs=f"{start}+{m.start()}c"; be=f"{start}+{m.end()}c"
            self.chat_history.tag_add("code_block", bs, be)
            try:
                lexer=get_lexer_by_name(m.group(1) or "text", stripall=True)
                idx=f"{start}+{m.start(2)}c"
                for tok,val in lex(m.group(2), lexer):
                    tag=str(tok).replace(".","_"); ln=len(val)
                    self.chat_history.tag_add(tag, idx, f"{idx}+{ln}c"); idx=f"{idx}+{ln}c"
            except: continue

    def send_message(self, event=None):
        prompt=self.input_text.get("1.0",tk.END).strip()
        if not prompt and not self.staged_images: return

        model_display_name = self.model_var.get()
        model_api_name = next((m["api"] for m in self.available_models if m["display"] == model_display_name), None)

        content_parts = []
        if prompt:
            content_parts.append({"type": "text", "text": prompt})

        if self.staged_images:
            if not model_api_name or model_api_name not in VISION_MODELS:
                messagebox.showerror("Model Error", f"The selected model '{model_display_name}' is not vision-capable. Please choose a vision model to send images.")
                return

            for img_path in self.staged_images:
                try:
                    with Image.open(img_path) as img:
                        output_buffer = io.BytesIO()
                        img.convert("RGB").save(output_buffer, format="JPEG")
                        base64_image = base64.b64encode(output_buffer.getvalue()).decode('utf-8')
                        content_parts.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        })
                except Exception as e:
                    messagebox.showerror("Image Error", f"Failed to process image {os.path.basename(img_path)}:\n{e}")
                    return

        final_content = content_parts if self.staged_images else prompt
        self.messages.append({"role": "user", "content": final_content})
        
        self.display_message("user", final_content)

        self.input_text.delete("1.0",tk.END)
        self.staged_images.clear()
        for widget in self.staging_area.winfo_children():
            widget.destroy()

        self.send_button.config(state=tk.DISABLED)
        self.input_text.config(state=tk.DISABLED)
        self.is_streaming = False
        threading.Thread(target=self._stream_worker_with_fallback, daemon=True).start()
        self.process_stream_queue()
    
    def _stream_worker_with_fallback(self):
        selected_display_name = self.model_var.get()
        try:
            start_index = next(i for i, model in enumerate(self.available_models) if model["display"] == selected_display_name)
        except StopIteration:
            start_index = 0
        fallback_order = self.available_models[start_index:] + self.available_models[:start_index]
        has_succeeded = False
        for model in fallback_order:
            self.stream_queue.put({"type": "status", "message": f"Trying model: {model['display']}..."})
            stream_had_content = False
            last_item_was_error = False
            for item in chat_with_cypher_alpha(self.messages, model["api"]):
                if item is None: break
                if isinstance(item, str):
                    if not self.is_streaming: self.is_streaming = True
                    self.stream_queue.put({"type": "content", "data": item, "model_name": model["display"]})
                    stream_had_content = True
                    last_item_was_error = False
                elif isinstance(item, dict) and item.get("type") == "error":
                    self.stream_queue.put(item)
                    last_item_was_error = True
                    if item.get("subtype") in ["auth_error", "rate_limit", "network"]:
                        has_succeeded = True
                        break
            if stream_had_content and not last_item_was_error:
                has_succeeded = True
                break
            if has_succeeded: break
        self.stream_queue.put(None)

    def process_stream_queue(self):
        try:
            item = self.stream_queue.get_nowait()
            if item is None:
                if self.is_streaming: self._on_stream_complete()
                else: self._reset_ui()
                return
            item_type = item.get("type")
            if item_type == "content":
                if not self.is_streaming:
                    self.is_streaming = True
                    self.current_stream_content = []
                    model_name = item.get("model_name", "Assistant")
                    self.chat_history.config(state=tk.NORMAL)
                    self.ai_header_start_index = self.chat_history.index(tk.END)
                    self.chat_history.insert(tk.END, f"{model_name}\n", ("assistant",))
                    self.ai_start_index = self.chat_history.index(tk.END)
                    self.chat_history.config(state=tk.DISABLED)
                self.chat_history.config(state=tk.NORMAL)
                self.current_stream_content.append(item["data"])
                self.chat_history.insert(tk.END, item["data"])
                self.chat_history.config(state=tk.DISABLED)
                self.chat_history.see(tk.END)
            elif item_type == "status":
                self.status_bar.config(text=item["message"])
            elif item_type == "error":
                if item.get("subtype") == "rate_limit": self._handle_rate_limit(item)
                else: self._handle_generic_error(item)
            elif item_type == "models_updated":
                self._repopulate_model_menu(item.get("models", []))
            elif item_type == "test_complete":
                failed_models = item.get("failed", [])
                if failed_models: self._remove_failed_models(failed_models)
                self.status_bar.config(text="Model testing complete.")
                self.menu_bar.entryconfig("Debug", state=tk.NORMAL)

            self.stream_queue.task_done()
            self.root.after(50, self.process_stream_queue)
        except queue.Empty:
            self.root.after(50, self.process_stream_queue)
        except Exception as e:
            print(f"Error in process_stream_queue: {e}")
            self._reset_ui()
            
    def _on_stream_complete(self):
        if not self.is_streaming:
            self._reset_ui()
            return
        self.status_bar.config(text="Stream finished. Finalizing...")
        self.chat_history.config(state=tk.NORMAL)
        full_streamed_content = "".join(self.current_stream_content)
        self.messages.append({"role": "assistant", "content": full_streamed_content})
        content_end_index = self.chat_history.index("end-1c")
        self._add_copy_button(content_end_index, full_streamed_content)
        self.chat_history.insert(tk.END, "\n\n")
        if hasattr(self, 'ai_start_index') and self.ai_start_index:
            self._highlight_code_in_range(self.ai_start_index, content_end_index)
        self.chat_history.config(state=tk.DISABLED)
        self.chat_history.see(tk.END)
        self._reset_ui()

    def start_model_fetch(self):
        self.status_bar.config(text="Fetching models from OpenRouter API...")
        threading.Thread(target=self._fetch_models_worker, daemon=True).start()
        self.process_stream_queue()

    def _fetch_models_worker(self):
        self.stream_queue.put({"type": "status", "message": "Fetching model list from API..."})
        try:
            url = "https://openrouter.ai/api/v1/models"
            resp = requests.get(url, timeout=20)
            resp.raise_for_status()
            all_models_data = resp.json().get("data", [])
            free_models = []
            for model_data in all_models_data:
                model_id = model_data.get('id', '')
                if model_id.endswith(':free'):
                    display_name = model_data.get('name', model_id).replace(" (free)", "").strip()
                    free_models.append({"display": display_name, "api": model_id})
            self.stream_queue.put({"type": "models_updated", "models": sorted(free_models, key=lambda x: x['display'])})
        except Exception as e:
            print(f"Model Fetch Error: {e}")
            self.stream_queue.put({"type": "status", "message": "Failed to fetch models."})
            self.stream_queue.put({"type": "models_updated", "models": []})

    def _repopulate_model_menu(self, models):
        self.available_models = models
        menu = self.model_menu["menu"]
        menu.delete(0, "end")
        if not self.available_models:
            self.model_var.set("No models found")
            self.model_menu.config(state=tk.DISABLED)
            self.status_bar.config(text="API fetch failed. No models loaded.")
            messagebox.showerror("API Error", "Could not fetch the model list from OpenRouter API.")
            return
        new_model_names = [m["display"] for m in self.available_models]
        for name in new_model_names:
            menu.add_command(label=name, command=tk._setit(self.model_var, name))
        self.model_var.set(new_model_names[0])
        self.model_menu.config(state=tk.NORMAL)
        self.status_bar.config(text="Ready")
        self.update_vision_status()
        
    def start_model_test(self):
        if messagebox.askyesno("Confirm Model Test", "This will send a 'TEST' message to every model sequentially and may take a long time.\n\nModels that fail will be removed from the dropdown list for this session.\n\nContinue?"):
            self.menu_bar.entryconfig("Debug", state=tk.DISABLED)
            threading.Thread(target=self._test_all_models_worker, daemon=True).start()
            self.process_stream_queue()

    def _test_all_models_worker(self):
        failed_models = []
        models_to_test = self.available_models[:]
        for model in models_to_test:
            self.stream_queue.put({"type": "status", "message": f"Testing: {model['display']}..."})
            is_successful = False
            has_failed = False
            messages = [{"role": "user", "content": "TEST"}]
            for item in chat_with_cypher_alpha(messages, model["api"]):
                if item is None: continue
                if isinstance(item, str) and item.strip():
                    is_successful = True
                    break
                elif isinstance(item, dict) and item.get("type") == "error":
                    subtype = item.get("subtype")
                    if subtype not in ["auth_error", "rate_limit", "network"]:
                        print(f"Model Failure: {model['display']:<40} | Reason: {item.get('message', 'Unknown error')}")
                        failed_models.append(model)
                    else:
                        self.stream_queue.put({"type": "status", "message": f"System Error during test. Stopping."})
                        self.stream_queue.put({"type": "test_complete", "failed": failed_models})
                        return
                    has_failed = True
                    break
            if not is_successful and not has_failed:
                print(f"Model Failure: {model['display']:<40} | Reason: No valid content in response.")
                failed_models.append(model)
        self.stream_queue.put({"type": "test_complete", "failed": failed_models})

    def _remove_failed_models(self, failed_models):
        current_selection = self.model_var.get()
        failed_apis = {m["api"] for m in failed_models}
        self.available_models = [m for m in self.available_models if m["api"] not in failed_apis]
        menu = self.model_menu["menu"]
        menu.delete(0, "end")
        new_model_names = [m["display"] for m in self.available_models]
        if not new_model_names:
            self.model_var.set("No models available")
            self.model_menu.config(state=tk.DISABLED)
            messagebox.showinfo("Model Test Complete", "All models failed the test.")
            return
        for name in new_model_names:
            menu.add_command(label=name, command=tk._setit(self.model_var, name))
        if current_selection not in new_model_names:
            self.model_var.set(new_model_names[0])
        else:
            self.model_var.set(current_selection)
        messagebox.showinfo("Model Test Complete", f"{len(failed_models)} model(s) failed and have been removed from the list.")

    def _handle_rate_limit(self, error_data):
        self._cleanup_failed_attempt()
        self.display_message("system_warning", error_data["message"], highlight=False)
        cooldown = error_data.get("cooldown", 15)
        self.send_button.config(state=tk.DISABLED)
        self.input_text.config(state=tk.DISABLED)
        self._update_cooldown_timer(cooldown)

    def _update_cooldown_timer(self, seconds_left):
        if seconds_left > 0:
            self.status_bar.config(text=f"Please wait... {seconds_left}s")
            self.root.after(1000, self._update_cooldown_timer, seconds_left - 1)
        else:
            self._reset_ui()
            
    def _handle_generic_error(self, error_data):
        self._cleanup_failed_attempt()
        self.display_message("system_warning", error_data["message"], highlight=False)
        self._reset_ui()
        
    def _cleanup_failed_attempt(self):
        if self.is_streaming and hasattr(self, 'ai_header_start_index') and self.ai_header_start_index:
            self.chat_history.config(state=tk.NORMAL)
            self.chat_history.delete(self.ai_header_start_index, "end-1c")
            self.chat_history.config(state=tk.DISABLED)

    def _reset_ui(self):
        self.send_button.config(state=tk.NORMAL)
        self.input_text.config(state=tk.NORMAL)
        self.status_bar.config(text="Ready (Ctrl+Enter to send)")
        self.is_streaming = False
        if hasattr(self, 'ai_header_start_index'): self.ai_header_start_index = None
        if hasattr(self, 'ai_start_index'): self.ai_start_index = None
        self.current_stream_content = []

    def export_chat(self):
        path=filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files","*.json"),("All files","*.*")])
        if not path: return
        with open(path,"w",encoding="utf-8") as f: json.dump(self.messages,f,indent=4)
        messagebox.showinfo("Success","Chat history saved.")

    def import_chat(self):
        if self.messages and not messagebox.askyesno("Load Chat","This will replace current conversation. Continue?"): return
        path=filedialog.askopenfilename(filetypes=[("JSON files","*.json"),("All files","*.*")])
        if not path: return
        with open(path,"r",encoding="utf-8") as f: data=json.load(f)
        self.new_chat(confirm=False)
        self.messages=data
        for m in self.messages:
            self.display_message(m["role"], m["content"])

    def new_chat(self, confirm=True):
        if confirm and not messagebox.askyesno("New Chat","Clear current conversation?"): return
        self.messages.clear()
        self.chat_history.config(state=tk.NORMAL)
        self.chat_history.delete("1.0",tk.END)
        self.chat_history.config(state=tk.DISABLED)
        greeting = "Hello! How can I help you today? Drag and drop images to chat with vision models."
        self.display_message("assistant", greeting, highlight=False)
        self.messages.append({"role": "assistant", "content": greeting})

    def toggle_theme(self):
        self.current_theme = "light" if self.current_theme=="dark" else "dark"
        self.apply_theme()

    def handle_right_click(self, event):
        """Checks if a right-click is on a code block and triggers a copy."""
        tags = self.chat_history.tag_names(f"@{event.x},{event.y}")
        if "code_block" in tags:
            self.copy_code_block(event)

    def copy_code_block(self, event):
        """Copy the fenced code block you right-clicked on."""
        idx = self.chat_history.index(f"@{event.x},{event.y}")
        ranges = self.chat_history.tag_ranges("code_block")
        for start,end in zip(ranges[0::2],ranges[1::2]):
            if (self.chat_history.compare(idx,">=",start) and self.chat_history.compare(idx,"<=",end)):
                raw = self.chat_history.get(start,end)
                cleaned=re.sub(r"^```[a-zA-Z]*\n|```$", "", raw).strip()
                if pyperclip:
                    try:
                        pyperclip.copy(cleaned)
                        self.status_bar.config(text="Code copied!")
                    except Exception as e:
                        self.status_bar.config(text=f"Clipboard error: {e}")
                else:
                    self.root.clipboard_clear()
                    self.root.clipboard_append(cleaned)
                    self.root.update()
                    self.status_bar.config(text="Code copied (fallback).")
                self.root.after(2000, lambda: self.status_bar.config(text="Ready (Ctrl+Enter to send)"))
                return
    
    def handle_drop(self, event):
        """Handle dropped files."""
        files = self.root.tk.splitlist(event.data)
        for f in files:
            if os.path.exists(f):
                if f.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                    if f not in self.staged_images:
                        self.staged_images.append(f)
                        self._display_staged_thumbnail(f)
                else:
                    self.status_bar.config(text=f"Unsupported file type: {os.path.basename(f)}")
                    self.root.after(3000, lambda: self.status_bar.config(text="Ready"))

    def _display_staged_thumbnail(self, file_path):
        """Creates and displays a thumbnail for a staged image."""
        thumb_frame = tk.Frame(self.staging_area, bd=1, relief=tk.RAISED)
        thumb_frame.pack(side=tk.LEFT, padx=5, pady=2)
        
        try:
            img = Image.open(file_path)
            img.thumbnail((64, 64))
            photo = ImageTk.PhotoImage(img)
            
            img_label = tk.Label(thumb_frame, image=photo)
            img_label.image = photo
            img_label.pack(side=tk.TOP)
            
            close_btn = tk.Button(thumb_frame, text="X", command=lambda p=file_path, f=thumb_frame: self._remove_staged_image(p, f), relief=tk.FLAT, font=("Segoe UI", 7))
            close_btn.pack(side=tk.BOTTOM, fill=tk.X, ipady=1, ipadx=1)

        except Exception as e:
            thumb_frame.destroy()
            messagebox.showerror("Image Error", f"Could not open image:\n{os.path.basename(file_path)}\n\nError: {e}")

    def _remove_staged_image(self, file_path, thumb_frame):
        """Removes an image from the staging area."""
        if file_path in self.staged_images:
            self.staged_images.remove(file_path)
        thumb_frame.destroy()

    def update_vision_status(self, *args):
        """Updates the label indicating if the selected model supports vision."""
        model_display_name = self.model_var.get()
        model_api_name = next((m["api"] for m in self.available_models if m["display"] == model_display_name), None)
        
        theme = THEMES[self.current_theme]
        if model_api_name in VISION_MODELS:
            self.vision_status_label.config(text="Vision Ready ✓", fg=theme["vision_fg_ok"])
        else:
            self.vision_status_label.config(text="Text Only ✗", fg=theme["vision_fg_no"])

# ----------------------------------------
# Startup Self-Tests
# ----------------------------------------
def run_startup_tests():
    errs=[]
    for theme,cfg in THEMES.items():
        for key in ["bg","fg","input_bg","btn_bg","btn_fg", "user_fg","ai_fg","menu_bg","menu_fg", "status_fg","system_fg", "vision_fg_ok", "vision_fg_no"]:
            if key not in cfg: errs.append(f"Theme '{theme}' missing '{key}'")
    
    methods_to_check = [
        "_create_widgets", "_configure_tags", "apply_theme", "display_message", 
        "_add_copy_button", "copy_message_content", "_highlight_code_in_range", 
        "send_message", "_stream_worker_with_fallback", "process_stream_queue", 
        "_on_stream_complete", "_fetch_models_worker", 
        "_repopulate_model_menu", "_handle_rate_limit", "_update_cooldown_timer", 
        "_handle_generic_error", "_cleanup_failed_attempt", "_reset_ui", 
        "export_chat", "import_chat", "new_chat", "toggle_theme", 
        "handle_right_click", "copy_code_block", "handle_drop", 
        "_display_staged_thumbnail", "_remove_staged_image", "update_vision_status",
        "start_model_test", "_test_all_models_worker", "_remove_failed_models", "start_model_fetch"
    ]

    for m in methods_to_check:
        if not hasattr(ChatUI,m): errs.append(f"ChatUI missing method '{m}'")
    
    if errs:
        for e in errs: print("Startup test error:",e)
        print("Exiting due to startup test failures."); exit(1)
    
    return not errs

# ----------------------------------------
# Application Entry Point
# ----------------------------------------
if __name__ == "__main__":
    if not run_startup_tests():
        exit(1)
        
    root = TkinterDnD.Tk() 
    app = ChatUI(root)
    root.mainloop()