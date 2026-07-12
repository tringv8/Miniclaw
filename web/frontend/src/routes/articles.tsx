import { createFileRoute } from "@tanstack/react-router"

import { ArticlesPage } from "@/components/articles/articles-page"

export const Route = createFileRoute("/articles")({
  component: ArticlesPage,
})
