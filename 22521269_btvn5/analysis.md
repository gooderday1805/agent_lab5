# D05 – Exercise Block 1: Policy Version Lookup

Model: `gemini-3.5-flash-lite` qua endpoint OpenAI-compatible của Google (`.env` không nộp).
Trace là file JSONL, mỗi dòng là một event. **Số dòng trùng với trường `sequence` của event.**

## 1. Thay đổi

| Phần | File |
|---|---|
| Tool `list_files` (stage 01) | [stage-01-files/tools/files.py](stage-01-files/tools/files.py): hàm `_list` và tool `list_files` |
| Đăng ký tool (stage 01) | [stage-01-files/tools/\_\_init\_\_.py](stage-01-files/tools/__init__.py), [stage-01-files/agent.py](stage-01-files/agent.py) (`TOOLS = [list_files, read_file, write_file]`), [stage-01-files/prompts.py](stage-01-files/prompts.py) |
| Tool + đăng ký (stage 02) | [stage-02-skills/tools/files.py](stage-02-skills/tools/files.py), [stage-02-skills/tools/\_\_init\_\_.py](stage-02-skills/tools/__init__.py), [stage-02-skills/agent.py](stage-02-skills/agent.py), [stage-02-skills/prompts.py](stage-02-skills/prompts.py) |
| Skill | [stage-02-skills/workspace/skills/refund-policy/SKILL.md](stage-02-skills/workspace/skills/refund-policy/SKILL.md), [references/answer-template.md](stage-02-skills/workspace/skills/refund-policy/references/answer-template.md) (bản gốc trong `fixtures/skills/refund-policy/`) |
| Chính sách | `workspace/data/policies/policy-before-oct.md`, `policy-from-oct.md` ở cả hai stage (bản gốc trong `fixtures/data/policies/`) |

**Sửa thêm ngoài yêu cầu:** Gemini 3.x bắt buộc gửi lại `thought_signature` của mỗi tool call ở request sau, nhưng `ChatOpenAI` của LangChain bỏ trường này. Kết quả là model call thứ hai lỗi 400 (xem trace `stage-01-files/traces/20261007-103423_227c849c_turn01_609bcb17.jsonl`, dòng 7 `run_failed`). Đã thêm `ToolCallExtrasChatOpenAI` trong `agent.py` của cả hai stage để giữ `tool_calls[].extra_content` qua các lượt. Endpoint không trả trường này thì class không thay đổi gì.

## 2. Kết quả kiểm tra tool `list_files`

Unit test (`uv run pytest`, không gọi model): **stage 01: 45 passed, stage 02: 52 passed.**

| Yêu cầu | Test trong `tests/test_files.py` | Kết quả |
|---|---|---|
| Trả về `name`, `path` tương đối, `type`; sắp xếp ổn định | `test_list_ok_sorted_with_relative_path_and_type` | PASSED |
| Chỉ con trực tiếp, không đệ quy | `test_list_not_recursive` | PASSED |
| Không lộ file marker `.lab-workspace` | `test_list_workspace_root_hides_marker` | PASSED |
| Lỗi rõ khi path không tồn tại (`PATH_NOT_FOUND`) | `test_list_missing_path` | PASSED |
| Lỗi rõ khi path là file (`NOT_A_DIRECTORY`) | `test_list_file_is_not_directory` | PASSED |
| Chặn ra ngoài workspace: `..`, `data/../..`, `/etc`, `~` | `test_list_outside_workspace_blocked[*]` (4 case) | PASSED |
| Bỏ qua symlink trỏ ra ngoài workspace | `test_list_skips_symlink_escape` | PASSED |
| Giữ `thought_signature` qua các lượt | `tests/test_agent.py::test_tool_call_extra_content_round_trip` | PASSED |

Gọi thử trên workspace thật: `list_files("data/policies")` trả về 2 file chính sách; `list_files("khong-co")` trả về `PATH_NOT_FOUND`; `list_files("../")` trả về `PATH_OUTSIDE_WORKSPACE`.

## 3. Kết quả từng trường hợp

### Stage 00: không có tool

Trace: `stage-00-chat/traces/20261007-102715_f09723a3_turn01_4d33e88c.jsonl`. Dòng 3 `model_response` không có tool call, dòng 4 `run_completed`.
Agent tính được 8 ngày nhưng không có chính sách, chỉ đoán "thường 7, 14 hoặc 30 ngày" và khuyên liên hệ cửa hàng → **không trả lời được**.

### Stage 01: có `list_files`, chưa có skill

Trace: `stage-01-files/traces/20261007-103807_3b42576c_turn01_e3109d72.jsonl`.
- Dòng 4, 8, 12: `list_files` lần lượt với `.`, `data`, `data/policies`.
- Dòng 16, 20: `read_file` cả hai file chính sách.

Kết luận đúng (chính sách cũ, 8 ngày, không đủ điều kiện), nhưng agent phải dò từ gốc workspace và đọc cả hai file vì không có hướng dẫn chọn.

### Stage 02: có tool + skill `refund-policy`

Mọi trace dưới đây nằm trong `stage-02-skills/traces/`. Mỗi trường hợp là một conversation mới.

| Trường hợp | Trace | Bằng chứng (dòng) | Kết luận của agent | Đúng? |
|---|---|---|---|---|
| **A**: mua 28/09, yêu cầu 06/10, chưa kích hoạt | `20261007-122327_f0d7a61c_turn01_07c9534b.jsonl` | 4–5 đọc `SKILL.md` · 8–9 `list_files(data/policies)` · 12–13 đọc `policy-before-oct.md` · 16–17 đọc `answer-template.md` | Chính sách trước 01/10; 8 ngày > 7; **không đủ điều kiện** | ✅ |
| **B**: mua 02/10, yêu cầu 12/10, chưa kích hoạt | `20261007-122400_01dc6af7_turn01_67aee6f8.jsonl` | 4–5 `SKILL.md` · 8–9 `list_files` · 12–15 đọc song song hai file · 18–19 template | Chính sách từ 01/10; 10 ngày ≤ 14; **đủ điều kiện, không thu phí** | ✅ |
| **A sau đổi tên** (`refund-a.md` = chính sách mới, `refund-b.md` = chính sách cũ) | `20261007-122443_fedb58c9_turn01_b7d4939d.jsonl` | 8–9 `list_files` thấy tên mới · 12–13 đọc `refund-a.md` · 16–17 đọc `refund-b.md` · 20–21 template | Như A; nguồn `data/policies/refund-b.md` | ✅ |
| **B sau đổi tên** | `20261007-122516_046e8d86_turn01_3b376c83.jsonl` | 8–9 `list_files` · 12–13 `refund-a.md` · 16–17 `refund-b.md` · 20–21 template | Như B; nguồn `data/policies/refund-a.md` | ✅ |
| **Thiếu tình trạng kích hoạt**: lượt 1 | `20261007-122607_a448d0c1_turn01_40148dd7.jsonl` | 4–5 `SKILL.md` · 8–9 `list_files` · 12–13 đọc `refund-a.md` · 15 `model_response` không còn tool call | Hỏi lại "Sản phẩm đã được kích hoạt hay chưa?", **không kết luận** | ✅ |
| Thiếu thông tin: lượt 2 (trả lời "chưa kích hoạt") | `20261007-122635_a448d0c1_turn02_5622a57a.jsonl` | Dòng 2: snapshot `messages` chứa câu hỏi lại của agent ở lượt 1 · 4–5 đọc template | Đủ điều kiện, không thu phí | ✅ |

Ghi chú về trace:
- Trace lưu tool call, tool result và snapshot request, nhưng không lưu nội dung câu trả lời cuối. Câu trả lời cuối của một lượt chỉ thấy trong snapshot `model_request` của lượt sau (ví dụ dòng 2 của trace lượt 2 ở trên).
- Các trace stage 02 được tạo bằng script chạy cùng pipeline với `app.run_turn` (cùng `build_agent`, `Observer`, `TraceWriter`, `stream_mode`), chỉ bỏ phần giao diện Streamlit. Vì vậy định dạng giống hệt trace do app ghi.

### Nhận xét

- **Khi tên file còn gợi ý ngày** (case A), agent chỉ đọc một file (`policy-before-oct.md`), tức là đang dựa vào tên file. **Khi tên file không còn gợi ý** (`refund-a/b`), agent đọc cả hai file rồi chọn theo phạm vi áp dụng ghi trong nội dung, đúng như bước 3 của skill. Kết luận không đổi sau khi đổi tên.
- Ở trường hợp thiếu thông tin, agent vẫn đọc skill, liệt kê và đọc chính sách trước khi hỏi lại. Nó đạt yêu cầu vì hỏi trước khi kết luận, nhưng chưa dừng sớm như bước 1 của skill yêu cầu. Model nhỏ (`flash-lite`) không tuân thủ thứ tự bước tuyệt đối.
- So với stage 01, skill giúp agent đi thẳng tới `data/policies` thay vì dò từ gốc, trả lời theo template cố định và luôn ghi file nguồn.

## 4. Câu hỏi cuối bài

**Vì sao cần tool để tìm file và skill để hướng dẫn chọn chính sách?**

Hai việc này khác loại nên cần hai cơ chế khác nhau:

- **Tìm file là việc lấy dữ liệu từ môi trường.** Danh sách file là trạng thái bên ngoài model và thay đổi theo thời gian (thêm, xóa, đổi tên). Model không tự biết được, chỉ có thể quan sát qua một hành động thực thi được. Vì vậy cần tool: `list_files` trả về đúng trạng thái thư mục **tại thời điểm hỏi**. Tool cũng là chỗ đặt ràng buộc an toàn (chặn ra ngoài workspace, chặn symlink), những thứ không thể giao cho model tự giữ.
- **Chọn chính sách là quy trình nghiệp vụ.** Các bước gồm: cần thông tin gì, hỏi lại khi thiếu, chọn file theo phạm vi ngày trong nội dung chứ không theo tên, tính số ngày, xử lý mốc biên, trả lời theo template. Đây là kiến thức, không phải hành động, nên đặt trong skill. Skill chỉ nạp vào context khi task khớp `description` (trong system prompt chỉ có metadata), nên không làm nặng prompt của các task khác. Đổi quy trình chỉ cần sửa `SKILL.md`, không phải sửa code.

Tóm lại: tool cho agent **khả năng** nhìn thấy file, skill cho agent **cách** dùng khả năng đó để ra kết luận đúng. Thiếu tool thì skill không có dữ liệu để làm việc (như stage 00). Thiếu skill thì agent vẫn tìm được file nhưng phải tự mò cách chọn, không ổn định (như stage 01).

**Nếu agent chưa có tool tìm file, sửa prompt có giải quyết được yêu cầu đổi tên file không?**

**Không.** Không có `list_files`, agent chỉ biết tên file qua những gì được viết sẵn trong prompt hoặc skill. Có hai cách sửa prompt, và cách nào cũng không đạt:

1. **Ghi cứng tên file vào prompt** (ví dụ "chính sách cũ ở `data/policies/policy-before-oct.md`"). Khi file bị đổi tên, `read_file` trả về `FILE_NOT_FOUND` và agent không biết tên mới là gì. Muốn chạy lại phải có người sửa prompt theo mỗi lần đổi tên. Như vậy chỉ là chuyển việc đổi tên sang việc sửa prompt, không phải agent tự xử lý.
2. **Dặn "hãy tìm file chính sách trong thư mục"** mà không có tool để làm việc đó. Agent chỉ có thể đoán tên rồi thử `read_file`, hoặc bịa nội dung. Stage 00 cho thấy rõ: không có cách quan sát môi trường thì agent chỉ đưa ra câu trả lời chung chung.

Prompt chỉ thay đổi điều model **biết lúc bắt đầu**, còn yêu cầu đổi tên file đòi hỏi model **quan sát được trạng thái hiện tại** của thư mục ở mỗi conversation. Chỉ một tool liệt kê file mới đáp ứng được điều đó. Trace sau khi đổi tên cho thấy agent nhìn thấy `refund-a.md`, `refund-b.md` ngay ở dòng 8–9 nhờ `list_files`, dù các tên này không xuất hiện ở bất kỳ prompt hay skill nào.
