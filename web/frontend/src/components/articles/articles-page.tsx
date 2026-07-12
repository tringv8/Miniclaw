import * as React from "react"
import { useTranslation } from "react-i18next"
import { toast } from "sonner"
import {
  IconTrash,
  IconDatabase,
  IconSearch,
  IconRefresh,
  IconExternalLink,
  IconLink,
} from "@tabler/icons-react"

import { PageHeader } from "@/components/page-header"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetFooter,
} from "@/components/ui/sheet"
import { getArticles, updateSheetsUrl, deleteArticle, type ArticleItem } from "@/api/articles"

const CATEGORIES = [
  "Tất cả",
  "Tụ điện sắt điện",
  "Màng mỏng điện cực",
  "Vật liệu perovskite",
  "Vật liệu áp điện",
  "Chất bán dẫn oxit",
  "Pin & lưu trữ năng lượng",
  "Khác",
]

function getCategoryIcon(category: string): string {
  switch (category) {
    case "Tụ điện sắt điện":
      return "⚡"
    case "Màng mỏng điện cực":
      return "🧪"
    case "Vật liệu perovskite":
      return "🔬"
    case "Vật liệu áp điện":
      return "🎚️"
    case "Chất bán dẫn oxit":
      return "💠"
    case "Pin & lưu trữ năng lượng":
      return "🔋"
    case "Khác":
      return "📁"
    default:
      return "📚"
  }
}

export function ArticlesPage() {
  const { t } = useTranslation()
  const [loading, setLoading] = React.useState(true)
  const [articles, setArticles] = React.useState<ArticleItem[]>([])
  const [googleSheetsUrl, setGoogleSheetsUrl] = React.useState("")
  const [sheetsUrlInput, setSheetsUrlInput] = React.useState("")
  const [savingUrl, setSavingUrl] = React.useState(false)
  const [activeCategory, setActiveCategory] = React.useState("Tất cả")
  const [searchQuery, setSearchQuery] = React.useState("")
  const [selectedArticle, setSelectedArticle] = React.useState<ArticleItem | null>(null)

  const loadData = React.useCallback(async () => {
    setLoading(true)
    try {
      const res = await getArticles()
      setArticles(res.articles || [])
      setGoogleSheetsUrl(res.google_sheets_url || "")
      setSheetsUrlInput(res.google_sheets_url || "")
    } catch (err) {
      console.error(err)
      toast.error("Không thể tải dữ liệu bài báo.")
    } finally {
      setLoading(false)
    }
  }, [])

  React.useEffect(() => {
    void loadData()
  }, [loadData])

  const handleSaveSheetsUrl = async () => {
    setSavingUrl(true)
    try {
      const res = await updateSheetsUrl(sheetsUrlInput.trim())
      setGoogleSheetsUrl(res.google_sheets_url)
      toast.success("Cấu hình Google Sheets thành công!")
    } catch (err) {
      console.error(err)
      toast.error("Không thể cập nhật link Google Sheets.")
    } finally {
      setSavingUrl(false)
    }
  }

  const handleDeleteArticle = async (id: string) => {
    if (!window.confirm("Bạn có chắc chắn muốn xóa bài báo này khỏi bộ lưu trữ?")) {
      return
    }
    try {
      await deleteArticle(id)
      setArticles((prev) => prev.filter((a) => a.id !== id))
      if (selectedArticle?.id === id) {
        setSelectedArticle(null)
      }
      toast.success("Đã xóa bài báo thành công!")
    } catch (err) {
      console.error(err)
      toast.error("Không thể xóa bài báo.")
    }
  }

  // Calculate counts for categories
  const getCategoryCount = React.useCallback(
    (category: string) => {
      if (category === "Tất cả") {
        return articles.length
      }
      return articles.filter((a) => a.category === category).length
    },
    [articles]
  )

  // Filtered articles list based on active category and search query
  const filteredArticles = React.useMemo(() => {
    let list = articles
    if (activeCategory !== "Tất cả") {
      list = list.filter((a) => a.category === activeCategory)
    }
    if (searchQuery.trim() !== "") {
      const q = searchQuery.toLowerCase()
      list = list.filter(
        (a) =>
          a.title.toLowerCase().includes(q) ||
          a.summary.toLowerCase().includes(q) ||
          (a.authors || "").toLowerCase().includes(q)
      )
    }
    // Sort by saved_at descending
    return [...list].sort((a, b) => b.saved_at.localeCompare(a.saved_at))
  }, [articles, activeCategory, searchQuery])

  return (
    <div className="flex h-full flex-col">
      <PageHeader
        title={t("navigation.articles")}
        children={
          <Button
            variant="outline"
            size="sm"
            onClick={() => void loadData()}
            disabled={loading}
          >
            <IconRefresh className={`size-4 ${loading ? "animate-spin" : ""}`} />
            {loading ? "Đang tải..." : "Tải lại"}
          </Button>
        }
      />

      <div className="min-h-0 flex-1 overflow-y-auto px-4 sm:px-6 py-4">
        {/* Google Sheets Config Banner */}
        <div className="bg-card text-card-foreground border-border/40 rounded-xl border p-4 shadow-sm mb-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div className="space-y-1">
            <div className="font-semibold flex items-center gap-1.5">
              <span>📊</span> Liên kết Google Sheets
            </div>
            <div className="text-muted-foreground text-xs">
              Nhập link bảng tính Google Sheets để phục vụ việc truy cập trực tiếp từ bài báo.
            </div>
          </div>
          <div className="flex flex-1 max-w-md gap-2 w-full">
            <Input
              type="text"
              className="bg-muted/50 border-border/40 flex-1 rounded-lg border px-3 py-1.5 text-sm outline-none focus:ring-1 focus:ring-primary transition"
              placeholder="Dán link Google Sheets của bạn vào đây..."
              value={sheetsUrlInput}
              onChange={(e) => setSheetsUrlInput(e.target.value)}
            />
            <Button
              onClick={() => void handleSaveSheetsUrl()}
              disabled={savingUrl}
              size="sm"
            >
              {savingUrl ? "Đang lưu..." : "Lưu"}
            </Button>
          </div>
        </div>

        {/* Categories Tabs & Search */}
        <div className="flex flex-col gap-4 md:flex-row md:items-center justify-between border-b border-border/20 pb-4 mb-6">
          <div className="flex flex-wrap gap-2">
            {CATEGORIES.map((cat) => {
              const count = getCategoryCount(cat)
              const isActive = activeCategory === cat
              return (
                <button
                  key={cat}
                  onClick={() => setActiveCategory(cat)}
                  className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium transition cursor-pointer border ${
                    isActive
                      ? "bg-foreground text-background border-foreground shadow-xs"
                      : "bg-muted/40 text-muted-foreground border-border/20 hover:bg-muted/80 hover:text-foreground"
                  }`}
                >
                  <span>{getCategoryIcon(cat)}</span>
                  <span>{cat}</span>
                  <span
                    className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                      isActive
                        ? "bg-background/20 text-background"
                        : "bg-muted-foreground/10 text-muted-foreground"
                    }`}
                  >
                    {count}
                  </span>
                </button>
              )
            })}
          </div>

          <div className="relative w-full md:w-64">
            <IconSearch className="absolute left-3 top-2.5 size-4 text-muted-foreground/60" />
            <input
              type="text"
              placeholder="Tìm kiếm bài viết..."
              className="w-full bg-muted/30 border border-border/20 rounded-full py-1.5 pl-9 pr-4 text-sm outline-none focus:border-primary/50 focus:ring-1 focus:ring-primary/20 transition-all"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        {/* Loading Indicator */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 text-muted-foreground">
            <IconDatabase className="size-8 animate-pulse mb-2" />
            <span className="text-sm">Đang tải danh sách bài báo...</span>
          </div>
        ) : filteredArticles.length === 0 ? (
          /* Empty State */
          <div className="flex flex-col items-center justify-center py-20 text-center border border-dashed border-border/30 rounded-2xl bg-muted/10">
            <div className="text-4xl mb-3">📚</div>
            <div className="text-sm font-semibold text-foreground">Không tìm thấy bài báo nào</div>
            <p className="text-muted-foreground text-xs max-w-xs mt-1 leading-relaxed">
              {searchQuery.trim() !== ""
                ? "Không tìm thấy kết quả phù hợp với từ khóa tìm kiếm của bạn."
                : "Chưa có bài báo nào được lưu trữ. Các bài báo tìm được từ Telegram hoặc Web sẽ tự động hiển thị ở đây."}
            </p>
          </div>
        ) : (
          /* Grid List */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 pb-12">
            {filteredArticles.map((article) => {
              const authorsList = article.authors
                ? article.authors.split(",").map((a) => a.trim())
                : []
              const dispAuthor =
                authorsList.length > 0
                  ? authorsList[0] + (authorsList.length > 1 ? " và cs" : "")
                  : "N/A"

              return (
                <div
                  key={article.id}
                  onClick={() => setSelectedArticle(article)}
                  className="bg-card text-card-foreground border-border/40 hover:border-primary/30 rounded-xl border p-5 shadow-xs hover:shadow-md transition-all duration-200 cursor-pointer flex flex-col justify-between group relative"
                >
                  <div>
                    <div className="flex items-start justify-between gap-2 mb-3">
                      <span className="text-[10px] uppercase font-semibold tracking-wider px-2 py-0.5 rounded-full bg-primary/10 text-primary">
                        {article.category}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {article.published_date || "N/A"}
                      </span>
                    </div>
                    <h3 className="font-semibold text-foreground/90 leading-snug line-clamp-2 group-hover:text-primary transition-colors text-sm">
                      {article.title}
                    </h3>
                    <p className="text-muted-foreground/85 text-xs mt-2.5 line-clamp-3 leading-relaxed">
                      {article.summary}
                    </p>
                  </div>
                  <div className="mt-5 pt-3.5 border-t border-border/10 flex items-center justify-between">
                    <span className="text-xs text-muted-foreground truncate max-w-[170px]" title={article.authors}>
                      👤 {dispAuthor}
                    </span>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={(e) => {
                          e.stopPropagation()
                          void handleDeleteArticle(article.id)
                        }}
                        className="text-muted-foreground/75 hover:text-destructive hover:bg-destructive/10 p-1.5 rounded-lg transition-colors cursor-pointer"
                        title="Xóa bài báo"
                      >
                        <IconTrash className="size-4" />
                      </button>
                    </div>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Article Detail Drawer Sidebar */}
      <Sheet open={selectedArticle !== null} onOpenChange={(open) => !open && setSelectedArticle(null)}>
        {selectedArticle && (
          <SheetContent className="w-full sm:max-w-md flex flex-col h-full bg-background border-l border-border/30 shadow-2xl p-0">
            <SheetHeader className="border-b border-border/10 p-5 bg-muted/5">
              <SheetTitle className="text-md font-bold pr-8">Chi tiết bài báo</SheetTitle>
              <SheetDescription className="text-[10px] font-mono opacity-60">
                ID: {selectedArticle.id}
              </SheetDescription>
            </SheetHeader>
            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">
              <h3 className="font-bold text-foreground text-sm leading-snug border-b border-border/10 pb-4">
                {selectedArticle.title}
              </h3>
              <div className="space-y-4 text-xs">
                <div className="flex items-start gap-3">
                  <span className="text-sm">👤</span>
                  <div>
                    <div className="font-semibold text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">Tác giả</div>
                    <div className="text-foreground/90 font-medium">{selectedArticle.authors || "N/A"}</div>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <span className="text-sm">📅</span>
                  <div>
                    <div className="font-semibold text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">Ngày đăng</div>
                    <div className="text-foreground/90 font-medium">{selectedArticle.published_date || "N/A"}</div>
                  </div>
                </div>

                <div className="flex items-start gap-3">
                  <span className="text-sm">🔗</span>
                  <div>
                    <div className="font-semibold text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">Link bài báo</div>
                    {selectedArticle.link ? (
                      <a
                        href={selectedArticle.link}
                        target="_blank"
                        rel="noreferrer"
                        className="text-primary hover:underline font-semibold break-all flex items-center gap-1"
                      >
                        {selectedArticle.link}
                        <IconExternalLink className="size-3 shrink-0" />
                      </a>
                    ) : (
                      <div className="text-muted-foreground">N/A</div>
                    )}
                  </div>
                </div>

                {selectedArticle.doi && (
                  <div className="flex items-start gap-3">
                    <span className="text-sm">📌</span>
                    <div>
                      <div className="font-semibold text-[10px] text-muted-foreground uppercase tracking-wider mb-0.5">DOI</div>
                      <a
                        href={selectedArticle.doi.startsWith("http") ? selectedArticle.doi : `https://doi.org/${selectedArticle.doi}`}
                        target="_blank"
                        rel="noreferrer"
                        className="text-primary hover:underline font-semibold break-all flex items-center gap-1"
                      >
                        {selectedArticle.doi}
                        <IconExternalLink className="size-3 shrink-0" />
                      </a>
                    </div>
                  </div>
                )}

                <div className="flex items-start gap-3 pt-1">
                  <span className="text-sm">📝</span>
                  <div className="flex-1">
                    <div className="font-semibold text-[10px] text-muted-foreground uppercase tracking-wider mb-1.5">Tóm tắt tiếng Việt</div>
                    <div className="bg-muted/30 text-foreground/80 leading-relaxed p-4 rounded-xl border border-border/10 whitespace-pre-line text-xs">
                      {selectedArticle.summary || "N/A"}
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <SheetFooter className="border-t border-border/10 p-5 bg-muted/10 mt-auto">
              {googleSheetsUrl ? (
                <a
                  href={googleSheetsUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 px-4 py-3 font-semibold text-white hover:bg-emerald-700 transition-colors shadow-sm text-sm"
                >
                  <IconLink className="size-4" />
                  Truy cập Google Sheets
                </a>
              ) : (
                <div className="text-center text-xs text-muted-foreground/80 w-full py-1">
                  Chưa có liên kết Google Sheets. Vui lòng cấu hình ở đầu trang.
                </div>
              )}
            </SheetFooter>
          </SheetContent>
        )}
      </Sheet>
    </div>
  )
}
