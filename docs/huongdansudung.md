# HƯỚNG DẪN SỬ DỤNG HỆ THỐNG MINICLAW DASHBOARD

Chào mừng bạn đến với tài liệu hướng dẫn sử dụng chi tiết hệ thống quản trị và tương tác với tác nhân thông minh **Miniclaw**. Giao diện điều khiển web của Miniclaw cung cấp một bộ công cụ toàn diện giúp cấu hình, theo dõi và quản lý tác nhân AI của bạn một cách trực quan và dễ dàng.

---

## MỤC LỤC

1. [Tổng quan về Giao diện & Trạng thái Gateway](#1-tổng-quan-về-giao-diện--trạng-thái-gateway)
2. [Chức năng Trò chuyện (Chat)](#2-chức-năng-trò-chuyện-chat)
3. [Quản lý Mô hình (Models)](#3-quản-lý-mô-hình-models)
4. [Thông tin Xác thực (Credentials)](#4-thông-tin-xác-thực-credentials)
5. [Quản lý Kỹ năng (Skills)](#5-quản-lý-kỹ-năng-skills)
6. [Quản lý Công cụ (Tools)](#6-quản-lý-công-cụ-tools)
7. [Cấu hình Kênh liên lạc (Channels)](#7-cấu-hình-kênh-liên-lạc-channels)
8. [Cài đặt Hệ thống (Config)](#8-cài-đặt-hệ-thống-config)
9. [Bộ lưu trữ Dữ liệu Bài báo (Articles)](#9-bộ-lưu-trữ-dữ-liệu-bài-báo-articles)
10. [Nhật ký Hoạt động (Logs)](#10-nhật-ký-hoạt-động-logs)

---

## 1. Tổng quan về Giao diện & Trạng thái Gateway

Thanh bên trái (Sidebar) của giao diện chứa menu điều hướng giúp bạn di chuyển nhanh chóng giữa các trang chức năng. 

Góc trên bên phải của màn hình luôn hiển thị trạng thái hiện tại của **Gateway** (Dịch vụ cổng kết nối trung tâm điều phối tin nhắn giữa các kênh và Agent):
*   **Trạng thái màu xanh (Đang chạy):** Gateway hoạt động bình thường, sẵn sàng kết nối hội thoại.
*   **Trạng thái màu đỏ / Gateway chưa chạy:** Trình duyệt sẽ hiển thị thông báo yêu cầu bật dịch vụ. Bạn có thể nhấn trực tiếp nút **"Khởi động Gateway"** ngay trên thanh tiêu đề của trang Web để bật dịch vụ mà không cần chạy lệnh thủ công qua terminal.
*   Các nút hành động nhanh đi kèm gồm **"Dừng Gateway"** hoặc **"Khởi động lại Gateway"** (cần thiết khi bạn áp dụng các thay đổi cấu hình sâu như cấu hình kênh liên lạc mới).

---

## 2. Chức năng Trò chuyện (Chat)

Đây là nơi bạn trực tiếp tương tác và trò chuyện với Tác nhân AI của hệ thống.

*   **Lựa chọn mô hình thông minh:** Ngay trên đầu thanh nhập tin nhắn, bạn có thể lựa chọn mô hình AI (Model) muốn sử dụng cho cuộc trò chuyện hiện tại (chọn từ danh sách các mô hình đã được bạn cấu hình trước đó).
*   **Khung hội thoại động:** Hiển thị toàn bộ lịch sử tin nhắn giữa người dùng và tác nhân AI dưới dạng bong bóng trò chuyện trực quan.
*   **Lịch sử phiên hội thoại (Sessions):** 
    *   Thanh bên của trang Chat liệt kê toàn bộ lịch sử các cuộc hội thoại cũ.
    *   Cho phép bạn nhanh chóng chuyển đổi qua lại giữa các phiên trò chuyện, tạo **"Cuộc trò chuyện mới"** hoặc nhấn biểu tượng Thùng rác để **"Xóa phiên"** giải phóng bộ nhớ.
*   **Trạng thái Suy nghĩ (Thinking Steps) & Phản hồi công cụ:**
    *   Khi Agent đang xử lý các tác vụ phức tạp hoặc đang tra cứu, hệ thống sẽ hiển thị các bước suy nghĩ thời gian thực như: *Đang suy nghĩ...*, *Đang phân tích yêu cầu của bạn...*, *Đang chuẩn bị phản hồi...*
    *   Nếu tùy chọn hiển thị phản hồi công cụ được bật, mỗi khi Agent gọi một công cụ (như đọc/ghi tệp tin, chạy lệnh hệ thống), một bản xem trước ngắn về tên công cụ và đối số truyền vào sẽ xuất hiện ngay trên khung chat, giúp bạn kiểm soát hoàn toàn những gì AI đang thực hiện trên máy tính của mình.

---

## 3. Quản lý Mô hình (Models)

Trang quản lý mô hình cho phép bạn đăng ký và tinh chỉnh kết nối tới các nhà cung cấp dịch vụ AI lớn hoặc các mô hình chạy cục bộ.

*   **Các nhà cung cấp được hỗ trợ:** OpenAI, Anthropic (Claude), Google Gemini, DeepSeek, Moonshot (Kimi), OpenRouter và dịch vụ chạy cục bộ Ollama (không cần API Key).
*   **Thao tác cơ bản:**
    *   **Thêm mô hình:** Nhập **Bí danh mô hình** (tên gợi nhớ để chọn khi chat), **Mã định danh mô hình** (định dạng `protocol/model-id`, ví dụ: `gemini/gemini-2.5-flash` hoặc `openai/gpt-4o`), và điền khóa API tương ứng.
    *   **Đặt làm mặc định:** Đánh dấu một mô hình làm mặc định để hệ thống tự động tải khi khởi tạo phiên chat mới.
    *   **Sửa / Xóa:** Dễ dàng thay đổi API key của mô hình hoặc xóa bỏ vĩnh viễn khỏi hệ thống.
*   **Tùy chọn cấu hình nâng cao (Advanced Options):**
    *   *URL gốc API (API Base URL):* Sử dụng các proxy trung gian hoặc các endpoint tùy chỉnh.
    *   *HTTP Proxy:* Điền địa chỉ proxy của bạn để vượt qua các rào cản kết nối mạng.
    *   *Thời gian chờ yêu cầu (Request Timeout):* Đặt thời gian ngắt kết nối khi gọi API quá lâu.
    *   *Giới hạn tốc độ (RPM):* Đặt số lượt yêu cầu tối đa mỗi phút để tránh bị khóa tài khoản AI do spam.
    *   *Mức suy luận (Thinking Level):* Cấu hình chế độ suy luận chuyên sâu đối với các mô hình hỗ trợ suy luận như DeepSeek-R1 hay o1/o3 (các mức: off, low, medium, high, xhigh, adaptive).
    *   *Nội dung body bổ sung (Extra Body):* Truyền các tham số JSON bổ sung cho request API.

---

## 4. Thông tin Xác thực (Credentials)

Trang này quản lý tập trung thông tin đăng nhập và xác thực của bạn cho các nền tảng AI.

*   Hỗ trợ đa dạng phương thức đăng nhập an toàn:
    *   **OAuth qua trình duyệt:** Tự động chuyển hướng đến trang đăng nhập của nhà cung cấp (ví dụ: Google hay OpenAI) để xác thực mà không cần bạn phải dán thủ công khóa API dài.
    *   **Mã thiết bị (Device Code):** Hiển thị mã xác minh để bạn nhập trên thiết bị hoặc tab trình duyệt khác để liên kết (ví dụ: xác thực tài khoản GitHub Copilot).
    *   **Lưu Token/Khóa thủ công:** Cho phép dán trực tiếp token truy cập và nhấn lưu.
*   Hiển thị rõ ràng trạng thái xác thực của từng dịch vụ: **Đã kết nối**, **Cần làm mới**, **Đã hết hạn** hoặc **Chưa đăng nhập**. Bạn có thể dễ dàng nhấn **"Đăng xuất"** bất kỳ lúc nào để xóa sạch thông tin xác thực khỏi hệ thống.

---

## 5. Quản lý Kỹ năng (Skills)

Kỹ năng (Skills) là tập hợp các tập tin hướng dẫn (`SKILL.md`) định nghĩa hành vi hoặc quy trình nghiệp vụ chuyên biệt mà bạn muốn huấn luyện cho Agent của mình.

*   **Quét và tải kỹ năng tự động:** Trang Kỹ năng sẽ quét và hiển thị tất cả các kỹ năng được nạp từ thư mục làm việc (Workspace), thư mục Miniclaw toàn cục (`.miniclaw/config/skills/`), và các kỹ năng hệ thống tích hợp sẵn.
*   **Nhập kỹ năng (Import Skill):** Cho phép bạn tải lên tệp tin nén hoặc thư mục chứa kỹ năng mới vào hệ thống.
*   **Trình đọc Kỹ năng (Skill Viewer):** Nhấn **"Xem"** để mở giao diện đọc trực quan nội dung tệp `SKILL.md` ngay trên Dashboard mà không cần dùng trình biên tập mã nguồn.
*   **Xóa kỹ năng:** Dễ dàng gỡ bỏ kỹ năng không còn cần thiết khỏi không gian làm việc của bạn.

---

## 6. Quản lý Công cụ (Tools)

Trang Công cụ hiển thị danh sách các tính năng hệ thống cốt lõi (tools) mà Agent có quyền gọi để thực hiện nhiệm vụ.

*   Trạng thái trực quan của từng công cụ:
    *   **Đã bật (Enabled - Màu xanh):** Agent đang có quyền sử dụng công cụ này.
    *   **Đã tắt (Disabled - Màu xám):** Đang bị tắt từ cấu hình hệ thống.
    *   **Bị chặn (Blocked - Màu đỏ):** Thiếu điều kiện tiên quyết của môi trường để hoạt động (ví dụ: công cụ yêu cầu hệ điều hành Linux nhưng bạn đang chạy trên Windows, hoặc thiếu công cụ cấp cha như `tools.skills`).
*   **Danh sách các công cụ hệ thống quan trọng:**
    *   `read_file`: Đọc nội dung tệp tin trong thư mục làm việc.
    *   `write_file`: Tạo mới hoặc ghi đè toàn bộ tệp tin.
    *   `edit_file`: Thay đổi hoặc sửa đổi một phần dòng code mục tiêu trong tệp tin.
    *   `list_dir`: Xem danh sách và cây thư mục.
    *   `exec`: Thực thi lệnh shell trực tiếp.
    *   `web_fetch`: Tải toàn bộ nội dung của trang web bất kỳ và tự động chuyển đổi định dạng HTML sang dạng văn bản thô hoặc Markdown sạch sẽ (giúp Agent đọc tài liệu trực tuyến).
    *   `message`: Gửi tin nhắn tiếp theo hoặc phản hồi trung gian tới các kênh chat đang hoạt động.
    *   `spawn`: Khởi chạy một Sub-agent (tác nhân phụ) và giao nhiệm vụ con để tăng hiệu năng xử lý song song.
    *   `cron`: Lên lịch cho các tác vụ lặp lại hoặc đặt đồng hồ báo thức kích hoạt Agent.

---

## 7. Cấu hình Kênh liên lạc (Channels)

Miniclaw cho phép Agent giao tiếp và phục vụ người dùng thông qua các nền tảng chat phổ biến được cấu hình.

*   **Các kênh hỗ trợ cấu hình:** Telegram và Web client.
*   **Cấu hình chi tiết cho từng kênh:**
    *   **Kênh Telegram:** Cung cấp các cấu hình như *Bot Token* (lấy từ BotFather) để Agent có thể gửi/nhận tin nhắn qua Telegram chat.
    *   **Kênh Web:** Các cài đặt dành riêng cho giao diện trò chuyện tích hợp sẵn trên Dashboard.
    *   *Chỉ khi được nhắc tên (Mention Only):* Tùy chọn để Agent chỉ trả lời khi được nhắc tên trực tiếp trong nhóm.
    *   *Hiển thị đang nhập (Typing Indicator):* Hiển thị trạng thái "đang nhập tin nhắn..." trên ứng dụng chat trong lúc Agent đang xử lý câu trả lời.
    *   *Tiền tố kích hoạt trong nhóm:* Cài đặt các ký tự đặc biệt giúp kích hoạt câu trả lời của Agent nhanh chóng.
*   *Lưu ý:* Sau khi thay đổi bất kỳ cấu hình kênh nào, bạn cần nhấn **"Khởi động lại Gateway"** trên thanh tiêu đề để áp dụng cấu hình mới.


---

## 8. Cài đặt Hệ thống (Config)

Trang này chứa toàn bộ các tham số cấu hình hoạt động cốt lõi của Miniclaw. Hệ thống hỗ trợ 2 chế độ hiển thị:
1.  **Cấu hình trực quan (Visual Config):** Cung cấp giao diện form nhập liệu, công tắc tắt bật rõ ràng cho từng nhóm cài đặt.
2.  **Cấu hình thô (Raw Config):** Hiển thị trực tiếp trình soạn thảo mã cấu hình dưới dạng JSON cho những người dùng nâng cao muốn copy-paste cấu hình nhanh.

Các phần cài đặt chính bao gồm:

### A. Tác nhân mặc định (Agent Defaults)
*   **Workspace:** Đường dẫn thư mục làm việc của tác nhân (nơi Agent được phép đọc ghi tệp tin).
*   **Giới hạn công cụ trong workspace:** Bật tính năng này để kích hoạt hộp cát (sandbox), ngăn chặn Agent đọc hoặc sửa các tệp tin hệ điều hành nằm ngoài Workspace được chỉ định.
*   **Chế độ trò chuyện tự nhiên (Split on marker):** Tự động chia các phản hồi rất dài của Agent thành nhiều đoạn tin nhắn ngắn hơn và gửi liên tục để giống với phong cách nhắn tin của con người.
*   **Phản hồi công cụ:** Bật/tắt và giới hạn độ dài hiển thị của đối số công cụ trên khung chat khi Agent chạy các công cụ hệ thống.
*   **Cấu hình giới hạn Token:** Thiết lập số token tối đa cho mỗi phản hồi và kích thước cửa sổ ngữ cảnh đầu vào (Context Window) của mô hình.
*   **Số vòng lặp công cụ tối đa:** Giới hạn số lần Agent được phép gọi công cụ liên tiếp trong một lượt yêu cầu để tránh hiện tượng AI bị lặp vô hạn khi gặp lỗi.
*   **Cài đặt múi giờ:** Cài đặt múi giờ IANA (ví dụ: `Asia/Ho_Chi_Minh`) để đồng bộ thời gian chạy của hệ thống và các tác vụ lên lịch Cron.

### B. Cổng kết nối (Gateway)
*   **Địa chỉ gateway (Gateway Host):** Giao diện mạng mà dịch vụ lắng nghe (mặc định là `0.0.0.0` để chấp nhận mọi kết nối).
*   **Cổng gateway (Gateway Port):** Cổng HTTP dịch vụ sử dụng (mặc định là `18790`).

### C. Công cụ thực thi lệnh (Exec Tool)
*   **Cho phép chạy lệnh:** Bật/tắt hoàn toàn công cụ thực thi lệnh shell `exec`. Khi tắt, Agent không thể chạy bất kỳ dòng lệnh nào.
*   **Thời gian chờ lệnh:** Đặt giới hạn thời gian chạy tối đa cho mỗi lệnh hệ thống để tránh các lệnh chạy ngầm bị treo vô hạn.
*   **Bảo mật nâng cao & Danh sách chặn (Blacklist/Whitelist):**
    *   *Cho phép chạy lệnh từ xa:* Cho phép hoặc ngăn chặn các yêu cầu chạy lệnh bắt nguồn từ môi trường bên ngoài không cục bộ.
    *   *Bật danh sách chặn lệnh nguy hiểm:* Chặn các lệnh chứa mẫu nguy hiểm.
    *   *Danh sách đen & Danh sách cho phép (Regex):* Điền các biểu thức chính quy (Regular Expression) trên mỗi dòng để chủ động cấm các lệnh nhạy cảm (ví dụ: cấm các lệnh chứa `rm -rf` hoặc `git push`) hoặc cho phép vượt qua bộ lọc.
    *   **Công cụ phát hiện mẫu lệnh (Pattern Detection Tool):** Một ô kiểm tra trực tiếp tích hợp sẵn trên giao diện. Bạn có thể gõ thử một câu lệnh hệ thống vào đây (ví dụ: `rm -rf /tmp`) và nhấn **"Kiểm tra"**, hệ thống sẽ báo ngay lập tức lệnh đó sẽ bị **Bị chặn** hay **Được phép** chạy theo tập quy tắc cấu hình hiện tại của bạn.

### D. Tác vụ Cron (Cron Tasks)
*   **Cho phép lệnh theo lịch:** Cho phép các tác vụ Cron đã lên lịch được phép tự động chạy lệnh shell mà không cần người dùng xác nhận lại thủ công.
*   **Thời gian chờ lệnh theo lịch:** Giới hạn thời gian tối đa chạy lệnh hệ thống của các job cron.

### E. Dịch vụ (Launcher Access)
*   Cấu hình dịch vụ Dashboard FastAPI: Cổng launcher (mặc định `18800`), quyền truy cập công khai từ bên ngoài mạng LAN, giới hạn dải mạng CIDR được phép truy cập, và tùy chọn **"Tự khởi động cùng hệ điều hành"** để Dashboard tự động chạy ngay khi bạn đăng nhập Windows/macOS.

### F. Thiết bị phần cứng (Devices)
*   Cấu hình kích hoạt tích hợp thiết bị phần cứng bổ trợ và theo dõi các sự kiện cắm/rút cổng USB trên máy chủ.

---

## 9. Bộ lưu trữ Dữ liệu Bài báo (Articles)

Đây là trang lưu trữ cơ sở dữ liệu chuyên biệt dành cho các bài báo nghiên cứu khoa học được thu thập bởi tác nhân Miniclaw.

*   **Phân loại theo danh mục học thuật:** Giao diện chia bài báo thành các bộ lọc trực quan:
    *   ⚡ *Tụ điện sắt điện (Ferroelectric capacitors)*
    *   🧪 *Màng mỏng điện cực (Electrode thin films)*
    *   🔬 *Vật liệu perovskite (Perovskite materials)*
    *   🎚️ *Vật liệu áp điện (Piezoelectric materials)*
    *   💠 *Chất bán dẫn oxit (Oxide semiconductors)*
    *   🔋 *Pin & lưu trữ năng lượng (Batteries & energy storage)*
    *   📁 *Khác*
*   **Bộ lọc tìm kiếm thông minh:** Ô tìm kiếm hỗ trợ lọc nhanh danh sách bài viết theo Tiêu đề, Tóm tắt hoặc Tên tác giả.
*   **Đồng bộ liên kết Google Sheets:**
    *   Trang cung cấp một thanh nhập **"Liên kết Google Sheets"** ở phía trên.
    *   Bạn dán liên kết bảng tính Google Sheets của bạn vào đây và nhấn **"Lưu"**. Tác nhân AI sẽ tự động đọc/ghi dữ liệu bài viết trực tiếp lên Google Sheets này để bạn dễ dàng quản lý số liệu nghiên cứu của mình.
*   **Xem chi tiết & Quản lý:** Nhấp vào một thẻ bài viết để đọc bản tóm tắt học thuật đầy đủ, danh sách tác giả, ngày công bố và nhấn biểu tượng Thùng rác để gỡ bỏ bài báo khỏi bộ lưu trữ nếu cần thiết.

---

## 10. Nhật ký Hoạt động (Logs)

Màn hình Nhật ký (Logs) giúp bạn theo dõi "sức khỏe" hệ thống theo thời gian thực.

*   Toàn bộ log gỡ lỗi của Gateway, Agent, các yêu cầu HTTP API gửi đi và phản hồi trả về được cập nhật liên tục trên màn hình.
*   Giúp bạn nhanh chóng phát hiện các lỗi phát sinh như: khóa API không hợp lệ, lỗi kết nối mạng, lệnh shell bị chặn hoặc cấu hình sai kênh chat.
*   Bạn có thể nhấn nút **"Xóa nhật ký"** để dọn sạch màn hình hiển thị logs cho dễ quan sát các dòng log mới tiếp theo.
