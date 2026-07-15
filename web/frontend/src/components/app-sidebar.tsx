import { IconChevronRight } from "@tabler/icons-react"
import {
  IconAtom,
  IconChevronsDown,
  IconChevronsUp,
  IconDatabase,
  IconKey,
  IconListDetails,
  IconMessageCircle,
  IconScale,
  IconSettings,
  IconSparkles,
  IconTools,
} from "@tabler/icons-react"
import { Link, useRouterState } from "@tanstack/react-router"
import * as React from "react"
import { useTranslation } from "react-i18next"

import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar"
import { useSidebarChannels } from "@/hooks/use-sidebar-channels"

interface NavItem {
  title: string
  url: string
  icon: React.ComponentType<{ className?: string }>
  translateTitle?: boolean
}

interface NavGroup {
  label: string
  defaultOpen: boolean
  items: NavItem[]
  isChannelsGroup?: boolean
}

interface LlmBenchmarkContextMenu {
  x: number
  y: number
}

const LLM_BENCHMARK_URL = "/llm-benchmark"
const LLM_BENCHMARK_STORAGE_KEY = "miniclaw.llmBenchmarkNavHidden"

const baseNavGroups: Omit<NavGroup, "items">[] = [
  {
    label: "navigation.chat",
    defaultOpen: true,
  },
  {
    label: "navigation.model_group",
    defaultOpen: true,
  },
  {
    label: "navigation.agent_group",
    defaultOpen: true,
  },
  {
    label: "navigation.services",
    defaultOpen: true,
  },
]

export function AppSidebar({ ...props }: React.ComponentProps<typeof Sidebar>) {
  const routerState = useRouterState()
  const { i18n, t } = useTranslation()
  const currentPath = routerState.location.pathname
  const [isLlmBenchmarkHidden, setIsLlmBenchmarkHidden] = React.useState(() => {
    try {
      return (
        globalThis.localStorage?.getItem(LLM_BENCHMARK_STORAGE_KEY) === "true"
      )
    } catch {
      return false
    }
  })
  const [llmBenchmarkMenu, setLlmBenchmarkMenu] =
    React.useState<LlmBenchmarkContextMenu | null>(null)
  const {
    channelItems,
    hasMoreChannels,
    showAllChannels,
    toggleShowAllChannels,
  } = useSidebarChannels({
    language: (i18n.resolvedLanguage ?? i18n.language ?? "").toLowerCase(),
    t,
  })

  const setLlmBenchmarkVisibility = React.useCallback((visible: boolean) => {
    const hidden = !visible
    setIsLlmBenchmarkHidden(hidden)
    try {
      if (hidden) {
        globalThis.localStorage?.setItem(LLM_BENCHMARK_STORAGE_KEY, "true")
      } else {
        globalThis.localStorage?.removeItem(LLM_BENCHMARK_STORAGE_KEY)
      }
    } catch {
      // Keep the current in-memory preference if browser storage is unavailable.
    }
    setLlmBenchmarkMenu(null)
  }, [])

  const openLlmBenchmarkMenu = React.useCallback((event: React.MouseEvent) => {
    event.preventDefault()
    event.stopPropagation()
    setLlmBenchmarkMenu({ x: event.clientX, y: event.clientY })
  }, [])

  React.useEffect(() => {
    if (!llmBenchmarkMenu) {
      return
    }

    const closeMenu = () => setLlmBenchmarkMenu(null)
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        closeMenu()
      }
    }

    globalThis.addEventListener("click", closeMenu)
    globalThis.addEventListener("contextmenu", closeMenu)
    globalThis.addEventListener("keydown", closeOnEscape)

    return () => {
      globalThis.removeEventListener("click", closeMenu)
      globalThis.removeEventListener("contextmenu", closeMenu)
      globalThis.removeEventListener("keydown", closeOnEscape)
    }
  }, [llmBenchmarkMenu])

  const navGroups: NavGroup[] = React.useMemo(() => {
    return [
      {
        ...baseNavGroups[0],
        items: [
          {
            title: "navigation.chat",
            url: "/",
            icon: IconMessageCircle,
            translateTitle: true,
          },
        ],
      },
      {
        ...baseNavGroups[1],
        items: [
          {
            title: "navigation.models",
            url: "/models",
            icon: IconAtom,
            translateTitle: true,
          },
          {
            title: "navigation.credentials",
            url: "/credentials",
            icon: IconKey,
            translateTitle: true,
          },
        ],
      },
      {
        label: "navigation.channels_group",
        defaultOpen: true,
        items: channelItems.map((item) => ({
          title: item.title,
          url: item.url,
          icon: item.icon,
          translateTitle: false,
        })),
        isChannelsGroup: true,
      },
      {
        ...baseNavGroups[2],
        items: [
          {
            title: "navigation.skills",
            url: "/agent/skills",
            icon: IconSparkles,
            translateTitle: true,
          },
          {
            title: "navigation.tools",
            url: "/agent/tools",
            icon: IconTools,
            translateTitle: true,
          },
        ],
      },
      {
        ...baseNavGroups[3],
        items: [
          {
            title: "navigation.config",
            url: "/config",
            icon: IconSettings,
            translateTitle: true,
          },
          {
            title: "navigation.articles",
            url: "/articles",
            icon: IconDatabase,
            translateTitle: true,
          },
          {
            title: "navigation.logs",
            url: "/logs",
            icon: IconListDetails,
            translateTitle: true,
          },
          {
            title: "So sánh LLM",
            url: LLM_BENCHMARK_URL,
            icon: IconScale,
            translateTitle: false,
          },
        ],
      },
    ]
  }, [channelItems])

  const displayedNavGroups = React.useMemo(
    () =>
      navGroups.map((group) => ({
        ...group,
        items: group.items.filter(
          (item) => item.url !== LLM_BENCHMARK_URL || !isLlmBenchmarkHidden,
        ),
      })),
    [isLlmBenchmarkHidden, navGroups],
  )

  return (
    <Sidebar
      {...props}
      className="bg-background border-r-border/20 border-r pt-3"
    >
      <SidebarContent className="bg-background">
        {displayedNavGroups.map((group) => (
          <Collapsible
            key={group.label}
            defaultOpen={group.defaultOpen}
            className="group/collapsible mb-1"
            onContextMenu={
              group.label === "navigation.services" && isLlmBenchmarkHidden
                ? openLlmBenchmarkMenu
                : undefined
            }
          >
            <SidebarGroup className="px-2 py-0">
              <SidebarGroupLabel asChild>
                <CollapsibleTrigger className="hover:bg-muted/60 flex w-full cursor-pointer items-center justify-between rounded-md px-2 py-1.5 transition-colors">
                  <span>{t(group.label)}</span>
                  <IconChevronRight className="size-3.5 opacity-50 transition-transform duration-200 group-data-[state=open]/collapsible:rotate-90" />
                </CollapsibleTrigger>
              </SidebarGroupLabel>
              <CollapsibleContent>
                <SidebarGroupContent className="pt-1">
                  <SidebarMenu>
                    {group.items.map((item) => {
                      const isLlmBenchmarkItem = item.url === LLM_BENCHMARK_URL
                      const isActive =
                        currentPath === item.url ||
                        (item.url !== "/" &&
                          currentPath.startsWith(`${item.url}/`))
                      return (
                        <SidebarMenuItem key={item.title}>
                          <SidebarMenuButton
                            asChild
                            isActive={isActive}
                            className={`h-9 px-3 ${isActive ? "bg-accent/80 text-foreground font-medium" : "text-muted-foreground hover:bg-muted/60"}`}
                          >
                            <Link
                              to={item.url}
                              onContextMenu={
                                isLlmBenchmarkItem
                                  ? openLlmBenchmarkMenu
                                  : undefined
                              }
                            >
                              <item.icon
                                className={`size-4 ${isActive ? "opacity-100" : "opacity-60"}`}
                              />
                              <span
                                className={
                                  isActive ? "opacity-100" : "opacity-80"
                                }
                              >
                                {item.translateTitle === false
                                  ? item.title
                                  : t(item.title)}
                              </span>
                            </Link>
                          </SidebarMenuButton>
                        </SidebarMenuItem>
                      )
                    })}
                    {group.isChannelsGroup && hasMoreChannels && (
                      <SidebarMenuItem key="channels-more-toggle">
                        <SidebarMenuButton
                          onClick={toggleShowAllChannels}
                          className="text-muted-foreground hover:bg-muted/60 h-9 px-3"
                        >
                          {showAllChannels ? (
                            <IconChevronsUp className="size-4 opacity-60" />
                          ) : (
                            <IconChevronsDown className="size-4 opacity-60" />
                          )}
                          <span className="opacity-80">
                            {showAllChannels
                              ? t("navigation.show_less_channels")
                              : t("navigation.show_more_channels")}
                          </span>
                        </SidebarMenuButton>
                      </SidebarMenuItem>
                    )}
                  </SidebarMenu>
                </SidebarGroupContent>
              </CollapsibleContent>
            </SidebarGroup>
          </Collapsible>
        ))}
        {llmBenchmarkMenu ? (
          <div
            className="bg-popover text-popover-foreground fixed z-50 min-w-32 rounded-md border p-1 shadow-md"
            style={{
              left: llmBenchmarkMenu.x,
              top: llmBenchmarkMenu.y,
            }}
            onClick={(event) => event.stopPropagation()}
            onContextMenu={(event) => event.preventDefault()}
          >
            <button
              type="button"
              className="hover:bg-accent hover:text-accent-foreground flex h-8 w-full items-center rounded-sm px-2 text-left text-sm disabled:pointer-events-none disabled:opacity-50"
              disabled={isLlmBenchmarkHidden}
              onClick={() => setLlmBenchmarkVisibility(false)}
            >
              Ẩn
            </button>
            <button
              type="button"
              className="hover:bg-accent hover:text-accent-foreground flex h-8 w-full items-center rounded-sm px-2 text-left text-sm disabled:pointer-events-none disabled:opacity-50"
              disabled={!isLlmBenchmarkHidden}
              onClick={() => setLlmBenchmarkVisibility(true)}
            >
              Mở
            </button>
          </div>
        ) : null}
      </SidebarContent>
      <SidebarRail />
    </Sidebar>
  )
}
