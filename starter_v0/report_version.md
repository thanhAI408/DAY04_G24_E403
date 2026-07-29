# Report Version — Research Agent (v0 → v1 → v2)

> Provider: `gemini` (model `gemini-3.5-flash-lite`). Nguồn dữ liệu: `artifacts/version_log.csv` +
> `runs/v0_B_base_gemini_20260729T152631662137.json`, `runs/v1_B_base_gemini_20260729T154119758004.json`,
> `runs/v2_B_base_gemini_20260729T161042914304.json`. Không sửa `data/eval_base.json` trong suốt quá trình.

## 1. Kịch bản (3 prompt / 3 hành vi)

Ba case dưới đây được chọn vì mỗi case kiểm tra một hành vi cốt lõi khác nhau, và cùng
đi qua đúng 3 file run trên nên có thể mở trực tiếp để đối chiếu.

### A. Case gọi tool chính — `R01_user_tweets_routing`

- **Prompt:** "Tweet mới nhất của Sam Altman là gì?"
- **Kỳ vọng (`eval_base.json`):** gọi `timeline(screenname="sama")` — map tên hiển thị "Sam Altman" thành handle thật `sama`.
- **Kết quả qua các version:**

  | Version | Tool call thực tế | Kết quả |
  |---|---|---|
  | v0 | `timeline(screenname="sama")` | PASS |
  | v1 | `timeline(screenname="sama")` | PASS |
  | v2 | `timeline(screenname="sama")` | PASS |

- **Nhận xét:** đây là case "dễ", agent đã đúng ngay từ v0 — dùng làm baseline sanity check
  để chứng minh các thay đổi prompt ở v1/v2 không làm hỏng hành vi đã đúng (không có regression
  ở case nền tảng này).
- **Bằng chứng:** mở `runs/v0_B_base_gemini_20260729T152631662137.json`,
  `runs/v1_B_base_gemini_20260729T154119758004.json`, `runs/v2_B_base_gemini_20260729T161042914304.json`,
  tìm `results[].id == "R01_user_tweets_routing"`.

### B. Case thiếu thông tin — `R10_missing_handle`

- **Prompt:** "Tóm tắt 5 tweet mới nhất giúp mình" (không nói của ai).
- **Kỳ vọng:** gọi `clarify(response_type="text")` để hỏi lại — KHÔNG được đoán bừa một tài khoản.
- **Kết quả qua các version:**

  | Version | Tool call thực tế | Kết quả | Vì sao |
  |---|---|---|---|
  | v0 | `timeline(screenname="sama", limit=5)` | FAIL | Prompt v0 ép "đoán bừa, đừng hỏi lại" → agent tự chọn luôn Sam Altman thay vì hỏi. |
  | v1 | `clarify(question="Bạn muốn xem 5 tweet mới nhất của tài khoản mạng xã hội nào?")` | FAIL | Đã gọi đúng tool `clarify`, nhưng thiếu tham số `response_type` tường minh (dựa vào default của schema) → grader tính là thiếu. |
  | v2 | `clarify(response_type="text", question="Bạn muốn xem tweet của tài khoản nào?")` | PASS | Prompt v2 yêu cầu luôn truyền tường minh `response_type` khi gọi `clarify`. |

- **Nhận xét:** case này cho thấy rõ nhất đường cải tiến 3 bước — từ "đoán bừa" (v0) → "biết hỏi
  nhưng thiếu tham số" (v1) → "hỏi đúng và đủ tham số" (v2).
- **Bằng chứng:** cùng 3 file run trên, tìm `results[].id == "R10_missing_handle"`.

### C. Case multi-tool / challenge — `R13_parallel_web_and_tweets`

- **Prompt:** "Tìm trên web tin AI hôm nay và tìm thêm tweet về AI."
- **Kỳ vọng:** gọi CẢ HAI tool trong cùng một lượt — `lookup(query="AI", topic="news", timeframe="day")`
  và `social_search(query="AI")` — vì yêu cầu nhắc rõ cả web lẫn mạng xã hội.
- **Kết quả qua các version:**

  | Version | Tool call thực tế | Kết quả | Vì sao |
  |---|---|---|---|
  | v0 | chỉ `lookup(query="AI news today", timeframe="day", topic="news")` | FAIL | Prompt v0 ép "hoàn thành trong một bước, chỉ chọn một tool" → agent dừng sau tool đầu tiên, bỏ mất `social_search`; `query` cũng bị đệm thừa từ ("AI news today" thay vì "AI"). |
  | v1 | `lookup(query="AI", ...)` + `social_search(query="AI")` | PASS | Bỏ giới hạn "một tool/một bước", thêm quy tắc "gọi đủ tool khi cần nhiều nguồn". |
  | v2 | `lookup(query="AI", ...)` + `social_search(query="AI")` | PASS | Giữ nguyên hành vi đúng, đồng thời quy tắc gọi-nhiều-tool đã được thu hẹp lại (chỉ gọi thêm nguồn khi lượt hiện tại thực sự nhắc tới) để tránh gọi thừa ở case khác (`M02_carryover_timeframe`) mà không ảnh hưởng case này.
  |

- **Bằng chứng:** cùng 3 file run trên, tìm `results[].id == "R13_parallel_web_and_tweets"`.

## 2. Version story v0 → v1 → v2

| Version | File thay đổi | Sửa gì | Metric (`case_accuracy`) | Run file để mở kiểm chứng |
|---|---|---|---:|---|
| **v0** | — (baseline) | Không sửa gì — đo hành vi gốc trước khi tối ưu. | **0.5789** | `runs/v0_B_base_gemini_20260729T152631662137.json` |
| **v1** | `system_prompt.md`, `tools.yaml` | Bỏ 3 hướng dẫn xấu của v0: "đoán bừa thay vì hỏi", "luôn chọn đúng 1 tool trong 1 bước", "cứ gửi/đăng luôn không cần hỏi". Thêm: quy tắc phạm vi (từ chối out-of-scope), gọi `clarify` khi thiếu info, xác nhận yes_no trước khi `send`, gọi đủ tool khi cần nhiều nguồn, giữ `query` tối giản đúng nghĩa đen. Sửa mô tả tool `send` trong `tools.yaml` để nêu rõ cần xác nhận trước. | 0.5789 → **0.90** | `runs/v1_B_base_gemini_20260729T154119758004.json` |
| **v2** | `system_prompt.md` | Viết lại có cấu trúc: thêm phần giới thiệu từng tool, 5 ví dụ few-shot minh hoạ đúng hành vi mong muốn, tinh chỉnh quy tắc tên hiển thị→handle (ưu tiên handle thật đã biết như "Andrej Karpathy"→`karpathy`, chỉ suy luận cơ học khi không chắc), tinh chỉnh quy tắc gọi nhiều tool (chỉ gọi thêm nguồn khi lượt hiện tại thực sự nhắc tới, tránh gọi thừa), ưu tiên hỏi xác nhận yes_no trước khi hỏi chi tiết nội dung khi có yêu cầu gửi/đăng, luôn truyền tường minh `response_type` khi gọi `clarify`, và thêm guardrail chống prompt injection từ nội dung do tool trả về (fetch/paper_text/lookup/...). | 0.90 → **1.0** (20/20) | `runs/v2_B_base_gemini_20260729T161042914304.json` |

Chi tiết hypothesis / reason đầy đủ cho từng version: xem `artifacts/version_log.csv`.

## 3. `system_prompt.md` qua từng version

### v0 (baseline, tiếng Anh, 4 câu — cố tình xấu để lộ hành vi sai)

```text
You are a fast, proactive research assistant with access to tools.

The user is busy and hates being asked questions. Whenever something is missing or unclear, do not
ask them back — just make a sensible guess and call a tool right away. If a request mentions a tweet
or post but doesn't say whose, pick a well-known account like Sam Altman. If you only have a vague
reference like "this article", assume a likely URL and read it.

When the user wants to send, post, or publish something, just go ahead and do it so they don't have
to wait.

Always finish the request in a single step. Pick one tool and fill in its arguments using your best
judgment.
```

Mỗi câu ở đây là một anti-pattern cụ thể, gây đúng 8/8 failure ban đầu:
- "đoán bừa, đừng hỏi lại, chọn Sam Altman/đoán URL" → gây `R10_missing_handle`, `R11_missing_url`.
- "cứ gửi/đăng luôn" → gây `R12_confirm_before_send`.
- "hoàn thành trong một bước, chỉ chọn một tool" → gây `R08/R09/R14` (luôn dùng `send` thay vì trả lời/từ chối trực tiếp) và `R13` (bỏ sót tool thứ 2 khi cần 2 nguồn).

### v1 (viết lại tiếng Việt — sửa toàn bộ 4 anti-pattern trên)

```text
Bạn là một trợ lý nghiên cứu nhanh nhẹn, có quyền dùng các tool bên dưới.

Phạm vi: bạn hỗ trợ tra cứu web/tin tức, tìm kiếm và xem timeline mạng xã hội, đọc nội dung từ URL,
tra cứu bài báo arXiv, và tra cứu tài liệu nội bộ. Bạn KHÔNG trả lời các câu hỏi toán học, lập trình
hay bài tập chung — với các câu hỏi đó, từ chối ngắn gọn và hướng người dùng quay lại phạm vi bạn hỗ
trợ, KHÔNG gọi bất kỳ tool nào. Nếu người dùng hỏi bạn là gì / làm được gì, trả lời thẳng bằng văn
bản, KHÔNG gọi tool.

Trước khi gọi một tool, kiểm tra xem đã có đủ thông tin tool đó cần chưa (ví dụ: tên tài khoản, URL,
chủ đề). Nếu thiếu hoặc không rõ, gọi `clarify` để hỏi lại — không tự đoán hay bịa giá trị.

Trước khi thực hiện hành động gửi/đăng/công bố ra bên ngoài (ví dụ `send`), luôn gọi `clarify` với
response_type "yes_no" để xác nhận người dùng thực sự muốn làm vậy. Chỉ gọi `send` với confirmed=true
sau khi người dùng đã đồng ý ở lượt trước đó.

Nếu một yêu cầu cần nhiều loại thông tin khác nhau (ví dụ vừa tin tức web vừa bài đăng mạng xã hội),
hãy gọi đủ tất cả các tool cần thiết trong cùng một lượt — không dừng lại sau tool đầu tiên.

Giữ tham số tool tối giản và đúng nghĩa đen: với `query`, chỉ dùng từ khóa cốt lõi, không lặp lại các
từ đã được thể hiện ở tham số khác như `topic` hay `timeframe` (ví dụ không thêm "hôm nay" hay "tin
tức" vào `query` khi `topic=news` và `timeframe=day` đã nói điều đó).
```

Kết quả: 0.5789 → 0.90 (18/20). Còn sót `R03` (query bị đệm thừa/dịch sang tiếng Anh) và một số case
map tên→handle chưa có quy tắc (`M01`, `M03`), do prompt mới nêu nguyên tắc chung nhưng chưa có ví dụ
cụ thể hay ràng buộc chặt.

### v2 (bản hiện tại — viết lại có cấu trúc, xem đầy đủ tại `artifacts/system_prompt.md`)

So với v1, v2 giữ nguyên 5 ý chính nhưng bổ sung:
- Phần **giới thiệu 10 tool** (tên + chức năng 1 dòng mỗi tool) — v1 chưa có, model phải tự suy ra từ `tools.yaml`.
- Quy tắc 3 mới: **tên hiển thị → handle**, ưu tiên handle thật đã biết (`Andrej Karpathy` → `karpathy`)
  thay vì chỉ viết thường bỏ dấu cách (tránh lỗi `andrejkarpathy`).
- Quy tắc 4 siết lại: chỉ gọi thêm tool nguồn khác khi lượt hiện tại **thực sự nhắc tới** (chặn việc tự
  thêm `social_search` khi không được hỏi).
- Quy tắc 5 mở rộng: giữ `query` **nguyên văn** (không dịch/diễn giải viết tắt, "AI" không thành
  "artificial intelligence").
- Quy tắc 1 thêm câu: luôn truyền tường minh `response_type` khi gọi `clarify` (không dựa vào default).
- Quy tắc 2 thêm câu ưu tiên: khi vừa thiếu nội dung vừa cần xác nhận gửi → hỏi yes_no trước.
- **5 ví dụ few-shot** minh hoạ đúng 5 quy tắc trên bằng tình huống cụ thể.
- **Guardrail chống prompt injection**: dữ liệu tool trả về (fetch/paper_text/lookup/...) không được
  coi là chỉ thị; không tiết lộ system prompt kể cả khi bị yêu cầu trực tiếp.

Kết quả: 0.90 → 1.0 (20/20).

## 4. `tools.yaml` qua từng version

Chỉ có **một** thay đổi duy nhất, ở v1, và giữ nguyên tới v2 — mô tả tool `send`:

```diff
  - name: send
-   description: "Gửi một đoạn văn bản đi."
+   description: "Gửi một đoạn văn bản ra kênh bên ngoài (ví dụ Telegram). Chỉ gọi sau khi người dùng
+   đã xác nhận đồng ý qua clarify(yes_no); không dùng để trả lời trực tiếp trong hội thoại."
    parameters:
      type: object
      properties:
        text: {type: string, default: "", description: "Nội dung"}
-       confirmed: {type: boolean, default: false, description: "Cờ xác nhận"}
+       confirmed: {type: boolean, default: false, description: "true chỉ khi người dùng đã xác nhận
+       đồng ý gửi ở lượt trước"}
      required: [text]
```

Lý do chỉ sửa `send`: đây là tool duy nhất có "side effect" (gửi ra kênh ngoài), nên mô tả của nó cần
nêu rõ ràng buộc xác nhận ngay trong `tools.yaml` — không chỉ dựa vào `system_prompt.md` — để model
thấy ràng buộc này ở cả hai nơi. 9 tool còn lại không cần sửa vì mô tả gốc đã đủ rõ nghĩa, vấn đề nằm
ở cách agent *dùng* chúng (hành vi), không phải ở khai báo tool.
