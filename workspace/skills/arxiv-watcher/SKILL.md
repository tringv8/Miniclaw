---
name: arxiv-watcher
description: Tìm kiếm và tóm tắt bài báo từ ArXiv. Dùng khi người dùng hỏi về nghiên cứu mới nhất, chủ đề cụ thể trên ArXiv, hoặc tóm tắt bài báo AI hàng ngày.
---

# ArXiv Watcher

Skill này kết nối ArXiv API để tìm bài báo khoa học theo từ khóa hoặc ArXiv ID.

## Workflow

### Bước 1 - Chạy script tìm kiếm

Script `search_arxiv.py` nằm cùng thư mục với skill này. Trước khi chạy, **tự dò đường dẫn đầy đủ** bằng cách:

```bash
# Dò script trong thư mục skill (ưu tiên)
find ~/.miniclaw/workspace/skills/arxiv-watcher/scripts -name "search_arxiv.py" 2>/dev/null || \
find ~/.miniclaw/workspace -name "search_arxiv.py" 2>/dev/null | head -1
```

Sau khi có đường dẫn đầy đủ, chạy:

```bash
python <đường_dẫn_đầy_đủ>/search_arxiv.py "<query>" [max_results]
```

Ví dụ (sau khi dò ra path):

```bash
python ~/.miniclaw/workspace/skills/arxiv-watcher/scripts/search_arxiv.py "WO3 OR tungsten trioxide" 5
python ~/.miniclaw/workspace/skills/arxiv-watcher/scripts/search_arxiv.py "LLM reasoning" 5
python ~/.miniclaw/workspace/skills/arxiv-watcher/scripts/search_arxiv.py "2512.08769"
```

Script tự chuẩn hóa query trước khi gọi ArXiv API:

- Chuỗi có `OR`, `AND`, `ANDNOT` sẽ được prefix từng vế bằng `all:`.
- Cụm từ nhiều chữ như `tungsten trioxide` sẽ được quote đúng cú pháp API.
- Khoảng trắng lạ từ Telegram, ví dụ non-breaking space, sẽ được chuẩn hóa.
- ArXiv ID vẫn được tra bằng `id_list`.

Nếu query trả kết quả rỗng hoặc quá rộng, thử lại bằng query đơn giản hơn qua script. Không tự gọi `web_fetch` vào `https://arxiv.org/search/...` làm fallback chính, vì trang search HTML của arXiv dễ trả HTTP 400 hoặc kết quả khó parse.

Script trả về cho mỗi bài:

- `Tiêu đề`
- `Tác giả` tối đa 4 người trong phần hiển thị
- `Ngày đăng`
- `Link` trang abstract trên arxiv.org
- `DOI` nếu có
- `Abstract` đầy đủ

### Bước 2 - Trình bày kết quả bằng tiếng Việt

Với mỗi bài tìm được, trình bày đúng mẫu dưới đây. Phải giữ nguyên các icon ở đầu từng dòng khi trả lời trên Telegram hoặc giao diện web.

---

**[STT]. [Tiêu đề bài báo]**
- 👤 **Tác giả**: [danh sách tác giả - tối đa 4 người]
- 📅 **Ngày đăng**: [YYYY-MM-DD]
- 🔗 **Link**: [link arxiv]
- 📌 **DOI**: [doi nếu có, bỏ qua nếu không có]
- 📝 **Tóm tắt**: [Tóm tắt abstract bằng tiếng Việt, 3-5 câu, súc tích, nêu rõ bài làm gì, vấn đề giải quyết là gì, đóng góp chính là gì]
- 🏷️ **Danh mục**: [mã - tên danh mục, ví dụ: PVK - Vật liệu perovskite; tối đa 2 nhãn]

---

Phần tóm tắt phải viết bằng tiếng Việt, diễn đạt lại ngắn gọn, không dịch nguyên văn abstract. Không bỏ icon trong phần trình bày kết quả.

### Bước 3 - Phân loại theo danh mục linh kiện

Sau khi tóm tắt, đối chiếu tiêu đề và abstract với bảng dưới để gán **1 hoặc 2 nhãn** phù hợp nhất.

**Quy tắc ưu tiên:**
1. Nhãn có từ khóa xuất hiện trong **tiêu đề** được ưu tiên hơn chỉ xuất hiện trong abstract.
2. Nếu 2 nhóm khớp ngang nhau, chọn nhóm có từ khóa **cụ thể hơn** (ví dụ: `BaTiO3` cụ thể hơn `thin film`).
3. Nếu bài liên quan đến vật liệu điện tử / bán dẫn **chưa có trong bảng** → tạo mã mới và bổ sung vào bảng (xem hướng dẫn bên dưới).
4. Chỉ dùng **OTH** khi bài thực sự không liên quan domain vật liệu điện tử/bán dẫn.

<!-- CATEGORY_TABLE_START -->
| Mã  | Tên danh mục                  | Từ khóa nhận diện                                                              |
|-----|-------------------------------|--------------------------------------------------------------------------------|
| FE  | Tụ điện sắt điện              | ferroelectric, BaTiO3, PZT, HfO2, polarization                                 |
| TFE | Màng mỏng điện cực            | thin film, electrode, ITO, FTO, sputtering                                      |
| PVK | Vật liệu perovskite           | perovskite, ABX3, halide perovskite, oxide perovskite                           |
| PZ  | Vật liệu áp điện              | piezoelectric, PVDF, AlN, ZnO, actuator                                         |
| OXS | Chất bán dẫn oxit             | oxide semiconductor, WO3, TiO2, V2O5, sensor                                   |
| BAT | Pin và lưu trữ năng lượng     | battery, lithium-ion, cathode, anode, electrolyte, supercapacitor, solar cell   |
| OTH | Khác                          | (không thuộc domain vật liệu điện tử/bán dẫn)                                  |
<!-- CATEGORY_TABLE_END -->

**Khi gặp vật liệu/linh kiện chưa có trong bảng:**

1. Tự đặt mã theo quy ước: viết tắt tên vật liệu bằng chữ in hoa, tối đa 5 ký tự
   - Ví dụ: GaN → `GAN`, MoS₂ → `MOS2`, graphene → `GRP`, TMD → `TMD`, OLED → `OLED`
2. Đặt tên danh mục ngắn gọn bằng tiếng Việt.
3. Liệt kê 3–6 từ khóa nhận diện tiêu biểu (tên hóa học, tên linh kiện, tên hiệu ứng).
4. Dùng `edit_file` để **thêm 1 dòng mới vào bảng** ngay trước dòng `| OTH |` trong file này:
   ```
   workspace/skills/arxiv-watcher/SKILL.md
   ```
   Ví dụ dòng cần chèn:
   ```
   | GAN | Vật liệu GaN/nitride          | GaN, gallium nitride, AlGaN, HEMT, nitride semiconductor                        |
   ```
5. Thông báo ngắn cho người dùng: `📌 Đã bổ sung danh mục mới: [MÃ] - [Tên]`

Điền nhãn vào trường `🏷️ **Danh mục**` trong mẫu Bước 2 ngay phía trên.


### Bước 4 - Lưu vào Google Sheets
Sau khi trình bày theo mẫu ở bước 2, tự động append ngầm thông tin bài báo vào Google Sheets bằng `gogcli`, không cần thông báo lại cho người dùng, chỉ gửi link khi được yêu cầu, lưu:

```bash
gogcli sheets append "<sheet_id>" "<tab_name>!A:G" --values-json '[["[STT]", "[YYYY-MM-DD]", "[Tiêu đề bài báo]", "[Tác giả]", "[Link]", "[Tóm tắt tiếng Việt]", "[Mã - Tên danh mục]"]]' --insert INSERT_ROWS
```

Nếu chưa có `<sheet_id>` hoặc `<tab_name>`, hỏi người dùng hoặc tìm các bảng tính có sẵn tên là `DulieuArXiv` trên Drive qua `gogcli drive search`.

Định dạng cột mặc định:

- Cột A: STT
- Cột B: Ngày xuất bản, nhất quán với sheet đang dùng
- Cột C: Tiêu đề bài báo
- Cột D: Tác giả
- Cột E: Link ArXiv
- Cột F: Tóm tắt tiếng Việt
- Cột G: **Danh mục linh kiện** (mã + tên, ví dụ: `PVK - Vật liệu perovskite`)


## Tham số script

| Tham số | Mô tả | Mặc định |
|---------|-------|----------|
| `query` | Từ khóa hoặc ArXiv ID | bắt buộc |
| `max_results` | Số lượng kết quả tối đa | `3` |

Script không cần thư viện ngoài, chỉ dùng Python built-in.
