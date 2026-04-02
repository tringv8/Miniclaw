Ổn hơn bản trước **rất nhiều**. Hướng này là đúng bài rồi. Nhưng em thấy vẫn còn vài chỗ nên siết lại để khỏi tự đạp mìn sau này.

## Cái ổn
- ✅ Tách **metadata** và **secrets**
- ✅ Không nhét raw secrets vào prompt
- ✅ Dùng **shared credential store**
- ✅ Tool runner lookup theo `user_id`, không theo channel
- ✅ `TOOL_ACCOUNTS.md` chỉ để agent biết trạng thái kết nối

Đó là khung chuẩn.

---

## Chỗ cần chỉnh thêm

### 1) `TOOL_ACCOUNTS.md` không nên là source of truth
File này chỉ nên là:
- human-readable
- agent-readable
- metadata phụ trợ

**Source of truth** vẫn nên là:
- credential store
- và nếu có thể, thêm 1 structured metadata store (`json/sqlite/db`)

Vì `.md` dễ lệch trạng thái với thực tế.
Ví dụ token bị revoke rồi nhưng file vẫn ghi `Status: connected`.

**Khuyến nghị:**
- `TOOL_ACCOUNTS.md` = bản tóm tắt cho agent/người đọc
- trạng thái thực = derive từ backend/store khi cần

---

### 2) `Status: connected` là chưa đủ
Nên có trạng thái rõ hơn, ví dụ:
- `connected`
- `expired`
- `missing`
- `revoked`
- `error`

Và nếu được thì thêm:
- `last_verified_at`
- `account`
- `scopes`

Ví dụ:
```md
## Gmail
- Account: user@gmail.com
- Status: expired
- Scopes: gmail.readonly, gmail.send
- Last verified: 2026-04-01T15:20:00Z
```

Như vậy agent đỡ nói bừa kiểu “đã connect” trong khi token chết.

---

### 3) Không nên dùng file secret JSON plaintext nếu tránh được
Đoạn này:

> `~/.miniclaw/secrets/{provider}_{user_id}.json`

Dùng tạm thì được, nhưng nên lưu ý:
- phải chmod chặt
- không commit
- không log
- không đưa vào workspace
- không cho agent đọc trực tiếp như tài liệu thường

Nếu làm nghiêm túc hơn, ưu tiên:
- OS keyring
- encrypted store
- sqlite + encryption
- secrets manager

Nếu hiện tại anh cần ship nhanh thì file JSON private vẫn chấp nhận được, **nhưng phải coi là bước chuyển tiếp**.

---

### 4) Phải có abstraction layer, đừng để từng tool tự đọc file
Điểm này quan trọng.

Đừng để mỗi tool tự làm:
- open file
- parse json
- tự xử expiry

Hãy ép mọi tool đi qua một module như anh viết:
- `save_credential`
- `get_credential`
- `delete_credential`

Và em đề nghị thêm:
- `get_credential_status`
- `refresh_credential_if_needed`
- `list_connected_tools`

Nếu không, sau này Gmail một kiểu, GitHub một kiểu, rất loạn.

---

### 5) Single-user hôm nay được, nhưng đừng hardcode chết `default`
Anh có ghi:

> hiện tại single-user nên user_id = "default"

Tạm ổn. Nhưng nên thiết kế API từ đầu theo dạng:
- `user_id` là parameter thật
- hiện tại caller chỉ truyền `"default"`

Đừng viết logic chết theo kiểu:
- path luôn là `gmail_default.json`
- code ngầm assume chỉ có 1 user

Nếu không sau này nâng multi-user sẽ rất mệt.

---

### 6) Thiếu bước “credential health check”
Hiện plan mới nói lưu và đọc. Nhưng chưa nói:
- khi token expired thì sao?
- refresh token ra sao?
- nếu refresh fail thì cập nhật metadata thế nào?

Nên có rule:
1. tool gọi `get_credential`
2. nếu expired nhưng refreshable → refresh
3. refresh thành công → update store
4. refresh fail → mark metadata/status là `expired` hoặc `revoked`
5. agent báo user reconnect

Đây là chỗ làm hệ thống “sống được” thay vì chỉ “đúng kiến trúc trên giấy”.

---

### 7) AGENTS.md instruction nên tránh bảo agent tự ghi mọi thứ quá tay
Câu này ổn về hướng:
> cập nhật trạng thái/account/scopes vào TOOL_ACCOUNTS.md

Nhưng nên thêm giới hạn:
- chỉ ghi metadata không nhạy cảm
- không ghi secret
- không ghi token/error dump đầy đủ
- chỉ cập nhật khi tool connection thực sự thay đổi

Nếu không agent sẽ spam file này.

---

## Phiên bản em chốt khuyến nghị

### `TOOL_ACCOUNTS.md`
Chỉ chứa:
- provider
- account label
- status
- scopes
- last verified
- notes ngắn

### `credentials.py`
Nên có ít nhất:
- `save_credential(user_id, provider, data)`
- `get_credential(user_id, provider)`
- `delete_credential(user_id, provider)`
- `get_credential_status(user_id, provider)`
- `refresh_if_needed(user_id, provider)`

### Tool runner flow
1. session → `user_id`
2. `credentials.get_credential(...)`
3. nếu cần thì refresh
4. gọi external service
5. update metadata/status nếu có thay đổi

---

## Kết luận
**Có, kế hoạch này ổn và đi đúng hướng.**
Nhưng để “bền” hơn, anh nên chỉnh thêm 4 ý sau:

1. `TOOL_ACCOUNTS.md` chỉ là metadata view, **không phải source of truth**
2. thêm status chuẩn: `connected/expired/revoked/error`
3. mọi tool phải đi qua `credentials.py`, không tự đọc file
4. thêm luồng refresh + health check

Nếu anh muốn, em có thể làm tiếp ngay:
- **rewrite plan này thành bản final sạch sẽ để giao cho coder**, hoặc
- viết luôn **spec `credentials.py` + format `TOOL_ACCOUNTS.md` chuẩn**.