'use client'

import React, { useState, useEffect, useRef } from 'react'
import { Card } from '@/components/ui/Card'
import { Button } from '@/components/ui/Button'
import { newsAPI } from '@/lib/api'
import { useNewsWebSocket, NewsItem } from '@/lib/useNewsWebSocket'
import { Radio, ExternalLink, TrendingUp, TrendingDown, Minus, ChevronDown, ChevronUp, ChevronLeft, ChevronRight, Sparkles, ArrowRight, ArrowUp, X, Search } from 'lucide-react'

// Helper for date formatting: MMM-DD-YYYY, 12hrs IST
const formatDate = (dateStr?: string) => {
    if (!dateStr) return { main: '', year: '' };
    try {
        const date = new Date(dateStr.includes('T') ? dateStr : dateStr.replace(' ', 'T'));
        const day = date.getDate().toString().padStart(2, '0');
        const month = new Intl.DateTimeFormat('en-US', { month: 'short', timeZone: 'Asia/Kolkata' }).format(date);
        const year = date.getFullYear().toString();
        const time = new Intl.DateTimeFormat('en-US', {
            timeZone: 'Asia/Kolkata',
            hour: 'numeric',
            minute: '2-digit',
            hour12: true
        }).format(date);

        return {
            main: `${time} IST, ${day}-${month}`,
            year: year
        };
    } catch (e) {
        return { main: dateStr, year: '' };
    }
}

// Sub-component for individual news items to manage expansion state and "seen" detection
function NewsCard({ item, onSeen }: { item: NewsItem, onSeen?: (id: number) => void }) {
    const [isExpanded, setIsExpanded] = useState(false)
    const [hasOverflow, setHasOverflow] = useState(false)
    const summaryRef = useRef<HTMLParagraphElement>(null)
    const cardRef = useRef<HTMLDivElement>(null)

    // Seen detection
    useEffect(() => {
        if (!onSeen) return

        const observer = new IntersectionObserver(([entry]) => {
            if (entry.isIntersecting) {
                onSeen(item.news_id)
                observer.disconnect()
            }
        }, {
            // Trigger when at least 20% of the card is visible
            threshold: 0.2,
            // Small rootMargin to trigger slightly before it enters
            rootMargin: '0px 0px -10% 0px'
        })

        if (cardRef.current) {
            observer.observe(cardRef.current)
        }

        return () => observer.disconnect()
    }, [item.news_id, onSeen])

    useEffect(() => {
        const checkOverflow = () => {
            const el = summaryRef.current
            if (el) {
                const isOverflowing = el.scrollHeight > el.clientHeight
                setHasOverflow(isOverflowing)
            }
        }

        checkOverflow()
        window.addEventListener('resize', checkOverflow)
        return () => window.removeEventListener('resize', checkOverflow)
    }, [item.summary])

    const getSentimentIcon = (sentiment?: string, colorClass?: string) => {
        const s = sentiment?.toLowerCase()
        const className = `w-3 h-3 ${colorClass || 'text-text-secondary'}`
        if (s === 'positive') return <TrendingUp className={className} />
        if (s === 'negative') return <TrendingDown className={className} />
        return <Minus className={className} />
    }

    const getImpactColor = (score?: number, sentiment?: string) => {
        const s = sentiment?.toLowerCase()
        // Eye-comfortable tinted pills with matching text colors
        if (s === 'positive') return { bg: 'bg-success/15', text: 'text-success', border: 'border-success/20' }
        if (s === 'negative') return { bg: 'bg-error/15', text: 'text-error', border: 'border-error/20' }
        // Default to warning/yellow tint
        return { bg: 'bg-warning/15', text: 'text-warning', border: 'border-warning/20' }
    }

    const getCardStyle = (sentiment?: string) => {
        const s = sentiment?.toLowerCase()
        if (s === 'positive') return 'border-success/20 hover:border-success/40 bg-success/[0.02]'
        if (s === 'negative') return 'border-error/20 hover:border-error/40 bg-error/[0.02]'
        return 'border-border/30 hover:border-primary/20 bg-panel/30'
    }

    return (
        <div ref={cardRef}>
            <Card className={`transition-all duration-200 overflow-hidden border ${getCardStyle(item.sentiment)}`}>
                <div className="p-2.5 px-3">
                    {/* Header Metadata Row - Impact follows metadata directly, Date on right */}
                    <div className="flex items-center justify-between gap-3 mb-1.5">
                        <div className="flex items-center gap-2 text-[10px] font-bold tracking-tight uppercase flex-grow min-w-0 flex-wrap">
                            <span className="text-primary/90 flex-shrink-0">{item.ticker || 'MARKET'}</span>
                            <span className="text-text-tertiary opacity-30 flex-shrink-0 text-[8px]">•</span>
                            <span className="text-text-secondary/80 flex-shrink-0">{item.exchange || 'GEN'}</span>

                            {item.company_name && (
                                <>
                                    <span className="text-text-tertiary opacity-30 flex-shrink-0 text-[8px]">•</span>
                                    <span className="text-text-tertiary font-bold flex-shrink-0">{item.company_name}</span>
                                </>
                            )}
                            <span className="text-text-tertiary opacity-30 flex-shrink-0 text-[8px]">•</span>


                            {/* Impact Score Badge - Sentiment-based solid color fill */}
                            {(() => {
                                const colors = getImpactColor(item.impact_score, item.sentiment);
                                return (
                                    <div className={`flex-shrink-0 flex items-center gap-1.5 px-2.5 py-0.5 ${colors.bg} ${colors.border} border rounded-full transition-colors`}>
                                        {getSentimentIcon(item.sentiment, colors.text)}
                                        <span className={`text-[9.5px] font-bold ${colors.text} uppercase tracking-tight whitespace-nowrap`}>
                                            {item.sentiment || 'NEUTRAL'} {item.impact_score && item.impact_score > 0 ? item.impact_score : ''}
                                        </span>
                                    </div>
                                );
                            })()}

                            {/* Source Link - after impact badge */}
                            {item.url && (
                                <a
                                    href={item.url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="flex items-center gap-1 text-[9px] font-bold text-primary hover:underline transition-all uppercase tracking-tight flex-shrink-0"
                                    title="View original source"
                                >
                                    <ExternalLink className="w-2.5 h-2.5" />
                                    Source
                                </a>
                            )}
                        </div>

                        {/* Right Side: Date with Year on next line */}
                        <div className="flex-shrink-0 text-right">
                            {(() => {
                                const { main, year } = formatDate(item.received_date);
                                return (
                                    <>
                                        <div className="text-[10px] font-bold text-text-tertiary/70 uppercase tracking-tighter tabular-nums leading-none">
                                            {main}
                                        </div>
                                        {year && (
                                            <div className="text-[9px] font-bold text-text-tertiary/60 uppercase tracking-tighter tabular-nums mt-0.5 leading-none">
                                                {year}
                                            </div>
                                        )}
                                    </>
                                );
                            })()}
                        </div>
                    </div>

                    {/* Main Content Area */}
                    <div className="flex gap-3 items-start">
                        <div className="flex-grow min-w-0 space-y-1">
                            <h3 className="text-[14px] font-semibold text-text-primary dark:text-[#f3f4f6] leading-snug">
                                {item.headline}
                            </h3>

                            <div className="relative">
                                <p
                                    ref={summaryRef}
                                    className={`text-[11px] text-text-secondary dark:text-[#9ca3af] opacity-80 leading-relaxed font-sans ${isExpanded ? '' : 'line-clamp-3'}`}
                                >
                                    {item.summary}
                                </p>

                                {hasOverflow && (
                                    <button
                                        onClick={() => setIsExpanded(!isExpanded)}
                                        className="text-[10px] font-bold text-primary hover:text-primary/80 flex items-center gap-0.5 mt-1 transition-colors uppercase tracking-wider"
                                    >
                                        {isExpanded ? (
                                            <>Show Less <ChevronUp className="w-3 h-3" /></>
                                        ) : (
                                            <>Show More <ChevronDown className="w-3 h-3" /></>
                                        )}
                                    </button>
                                )}
                            </div>
                        </div>

                    </div>
                </div>
            </Card>
        </div>
    )
}

export default function NewsPage() {
    const [news, setNews] = useState<NewsItem[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [lastUpdated, setLastUpdated] = useState<Date | null>(null)

    // Pagination state
    const [page, setPage] = useState(1)
    const [pageSize, setPageSize] = useState(20)
    const [total, setTotal] = useState(0)
    // Derived state for pagination
    const totalPages = Math.max(1, Math.ceil(total / pageSize))

    // Refs for WebSocket handler to prevent stale closures
    const pageRef = useRef(page)
    const pageSizeRef = useRef(pageSize)

    useEffect(() => { pageRef.current = page }, [page])
    useEffect(() => { pageSizeRef.current = pageSize }, [pageSize])

    // Notification state
    const [isScrolledDown, setIsScrolledDown] = useState(false)
    const [unseenIds, setUnseenIds] = useState<Set<number>>(new Set())
    const [showNotification, setShowNotification] = useState(false)

    // Search state
    const [searchQuery, setSearchQuery] = useState('')
    const [debouncedSearch, setDebouncedSearch] = useState('')

    // Debounce search input
    useEffect(() => {
        const timer = setTimeout(() => {
            setDebouncedSearch(searchQuery)
        }, 500)
        return () => clearTimeout(timer)
    }, [searchQuery])

    // Reset pagination when search changes
    useEffect(() => {
        if (page !== 1) setPage(1)
    }, [debouncedSearch])

    const { isConnected: wsConnected } = useNewsWebSocket((newNews) => {
        console.log('[NewsPage] Received real-time news:', newNews.news_id);

        const currentPage = pageRef.current
        const main = document.querySelector('main')
        const scrolled = main ? main.scrollTop > 300 : false

        // Update news list ONLY if on page 1
        if (currentPage === 1) {
            setNews(prev => {
                const exists = prev.some(item => item.news_id === newNews.news_id)
                if (exists) return prev
                return [newNews, ...prev].slice(0, 100)
            })
        }

        // Always update total for pagination summary
        setTotal(prev => prev + 1)
        setLastUpdated(new Date())

        // Show notification if:
        // 1. Scrolled down on Page 1
        // 2. Anywhere on Page 2+
        if ((scrolled && currentPage === 1) || currentPage > 1) {
            setUnseenIds(prev => {
                const next = new Set(prev)
                next.add(newNews.news_id)
                return next
            })
            setShowNotification(true)
        }
    })

    // Scroll listener to clear notifications when user reaches top of Page 1
    useEffect(() => {
        const main = document.querySelector('main')
        if (!main) return

        const handleScroll = () => {
            const threshold = 300
            if (main.scrollTop > threshold) {
                setIsScrolledDown(true)
            } else {
                setIsScrolledDown(false)
                // ONLY clear notifications if we are on Page 1
                // On Page 2+, reaching the top just means we are at the top of old news
                if (page === 1) {
                    setShowNotification(false)
                    setUnseenIds(new Set())
                }
            }
        }

        main.addEventListener('scroll', handleScroll)
        return () => main.removeEventListener('scroll', handleScroll)
    }, [page]) // Add page as dependency to respect page check

    const scrollToTop = () => {
        const main = document.querySelector('main')
        if (main) {
            main.scrollTo({ top: 0, behavior: 'instant' })
        }
    }

    const handleJumpToRecent = () => {
        const main = document.querySelector('main')
        if (main) {
            main.scrollTo({ top: 0, behavior: 'smooth' })
        }

        // Reset to page 1 to show the new news
        if (page !== 1) {
            setPage(1)
        }

        setShowNotification(false)
        setUnseenIds(new Set())
    }

    const handleSeen = (id: number) => {
        setUnseenIds(prev => {
            if (!prev.has(id)) return prev
            const next = new Set(prev)
            next.delete(id)
            if (next.size === 0) setShowNotification(false)
            return next
        })
    }

    useEffect(() => {
        console.log('[NewsPage] WebSocket connection status:', wsConnected ? 'CONNECTED' : 'DISCONNECTED');
    }, [wsConnected])

    // Generate page numbers with ellipsis (same as Symbols Master)
    const getPageNumbers = () => {
        const pages: (number | string)[] = []
        const maxVisible = 5

        if (totalPages <= maxVisible) {
            for (let i = 1; i <= totalPages; i++) {
                pages.push(i)
            }
        } else {
            pages.push(1)
            if (page <= 3) {
                for (let i = 2; i <= 4; i++) {
                    pages.push(i)
                }
                pages.push('ellipsis')
                pages.push(totalPages)
            } else if (page >= totalPages - 2) {
                pages.push('ellipsis')
                for (let i = totalPages - 3; i <= totalPages; i++) {
                    pages.push(i)
                }
            } else {
                pages.push('ellipsis')
                for (let i = page - 1; i <= page + 1; i++) {
                    pages.push(i)
                }
                pages.push('ellipsis')
                pages.push(totalPages)
            }
        }
        return pages
    }

    const loadNews = async () => {
        try {
            setLoading(true)
            const response = await newsAPI.getNews({
                page: page,
                page_size: pageSize,
                search: debouncedSearch || undefined
            })

            // Handle paginated response
            if (response && response.news) {
                setNews(response.news)
                setTotal(response.total)
            } else if (Array.isArray(response)) {
                // Fallback for old API if needed
                setNews(response)
                setTotal(response.length)
            }

            setLastUpdated(new Date())
            setError(null)
        } catch (err: any) {
            setError(err.message || 'Failed to load news')
            console.error('Error loading news:', err)
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        loadNews()
        scrollToTop()
    }, [page, pageSize, debouncedSearch])

    return (
        <div className="relative">
            {/* Sticky Header - Fixed at the very top */}
            <div className="sticky top-0 z-20 bg-page-bg/95 dark:bg-[#0e1628]/95 backdrop-blur-md -mx-4 -mt-4 px-4 py-4 mb-4 border-b border-border/10">
                <div className="flex items-center justify-between gap-4">
                    <div className="min-w-0">
                        <div className="flex items-center gap-3 mb-1">
                            <h1 className="text-xl font-sans font-semibold text-text-primary dark:text-[#e5e7eb] flex items-center gap-2">
                                News
                                <div className="flex items-center gap-1.5 px-2.5 py-1 bg-primary/10 rounded-lg border border-primary/20">
                                    <Sparkles className="w-3.5 h-3.5 text-primary" />
                                    <span className="text-[10px] font-bold text-primary uppercase tracking-wider">AI Powered</span>
                                </div>
                            </h1>
                            <div className="flex items-center gap-1.5 px-2 py-0.5 bg-success/10 rounded-full">
                                <Radio className={`w-3 h-3 text-success ${wsConnected ? 'animate-pulse' : ''}`} />
                                <span className="text-[9px] font-bold text-success uppercase tracking-wider tabular-nums">
                                    {wsConnected ? 'LIVE' : 'OFFLINE'}
                                </span>
                            </div>
                        </div>
                        <p className="text-xs font-sans text-text-secondary dark:text-[#9ca3af] truncate">
                            AI-enriched market insights delivered in real-time
                            {lastUpdated && (
                                <span className="ml-2 text-[9px] opacity-70">
                                    • Updated: {lastUpdated.toLocaleTimeString()}
                                </span>
                            )}
                        </p>
                    </div>

                    {/* Search Field */}
                    <div className="relative max-w-sm w-full">
                        <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
                            <Search className="h-4 w-4 text-text-tertiary" />
                        </div>
                        <input
                            type="text"
                            placeholder="Search headline, summary or ticker..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                            className="w-full bg-panel/50 dark:bg-panel/20 border border-border/50 rounded-xl py-2 pl-10 pr-10 text-xs focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary/40 transition-all placeholder:text-text-tertiary font-medium"
                        />
                        {searchQuery && (
                            <button
                                onClick={() => setSearchQuery('')}
                                className="absolute inset-y-0 right-3 flex items-center text-text-tertiary hover:text-text-primary transition-colors"
                            >
                                <X className="h-3.5 w-3.5" />
                            </button>
                        )}
                    </div>
                </div>
            </div>

            {/* Smart Notification - Floating on right */}
            {showNotification && unseenIds.size > 0 && (
                <div
                    className="fixed bottom-10 right-8 z-50 animate-in fade-in slide-in-from-right-8 duration-300"
                    style={{
                        animation: 'slideInRight 0.4s cubic-bezier(0.16, 1, 0.3, 1)'
                    }}
                >
                    <div className="flex items-center bg-primary dark:bg-[#3b82f6] text-white p-1 rounded-2xl shadow-[0_8px_40px_rgb(59,130,246,0.4)] border border-white/10 backdrop-blur-sm">
                        <button
                            onClick={handleJumpToRecent}
                            className="flex items-center gap-3 py-2.5 pl-3 pr-4 rounded-xl hover:bg-white/10 transition-all duration-200 group"
                        >
                            <div className="flex items-center justify-center w-8 h-8 rounded-xl bg-white/20 group-hover:bg-white/30 transition-colors">
                                <ArrowUp className="w-4 h-4 text-white animate-bounce" />
                            </div>
                            <div className="flex flex-col items-start leading-none min-w-[120px]">
                                <span className="text-[10px] font-bold uppercase tracking-widest opacity-80 mb-1">Jump To Recent</span>
                                <span className="text-[13px] font-bold tracking-tight">
                                    {unseenIds.size} New {unseenIds.size === 1 ? 'Update' : 'Updates'}
                                </span>
                            </div>
                        </button>

                        <div className="w-px h-8 bg-white/20 mx-0.5" />

                        <button
                            onClick={() => {
                                setShowNotification(false);
                                setUnseenIds(new Set());
                            }}
                            className="p-3 rounded-xl hover:bg-red-500/20 hover:text-red-200 transition-all duration-200 text-white/50 group"
                            title="Dismiss"
                        >
                            <X className="w-4 h-4" />
                        </button>
                    </div>
                </div>
            )}

            {/* Animation styles */}
            <style jsx>{`
                @keyframes slideInRight {
                    from { transform: translateX(120%); opacity: 0; }
                    to { transform: translateX(0); opacity: 1; }
                }
            `}</style>

            {loading && news.length === 0 ? (
                <div className="py-20 text-center text-text-secondary">Loading real-time news...</div>
            ) : error ? (
                <div className="py-20 text-center text-error bg-error/5 rounded-xl border border-error/10">{error}</div>
            ) : (
                <>
                    <div className="grid grid-cols-1 gap-2.5">
                        {news.map((item) => (
                            <NewsCard
                                key={item.news_id}
                                item={item}
                                onSeen={unseenIds.has(item.news_id) ? handleSeen : undefined}
                            />
                        ))}
                    </div>

                    {/* Pagination Controls - Styled like Symbols Master */}
                    {!loading && total > 0 && (
                        <div className="mt-8 pt-6 border-t border-border flex items-center justify-between flex-wrap gap-4 pb-10">
                            {/* Rows per page selector */}
                            <div className="flex items-center gap-2">
                                <span className="text-xs font-medium text-text-secondary uppercase tracking-wider">Rows per page:</span>
                                <select
                                    value={pageSize}
                                    onChange={(e) => {
                                        setPageSize(Number(e.target.value))
                                        setPage(1)
                                    }}
                                    className="px-2 py-1 text-xs border border-border/50 rounded bg-panel/50 text-text-primary focus:outline-none focus:ring-1 focus:ring-primary/30 font-bold"
                                    disabled={loading}
                                >
                                    <option value={10}>10</option>
                                    <option value={20}>20</option>
                                    <option value={50}>50</option>
                                    <option value={100}>100</option>
                                </select>
                            </div>

                            {/* Page navigation */}
                            <div className="flex items-center gap-1">
                                <Button
                                    variant="secondary"
                                    size="sm"
                                    onClick={() => setPage(prev => Math.max(1, prev - 1))}
                                    disabled={loading || page === 1}
                                    className="h-8 px-3 rounded-lg border border-border/50 hover:bg-primary/5 text-[11px] font-bold uppercase tracking-tight"
                                >
                                    <ChevronLeft className="w-3.5 h-3.5 mr-1" /> Previous
                                </Button>

                                {/* Page numbers with ellipsis */}
                                <div className="flex items-center gap-1 mx-1">
                                    {getPageNumbers().map((pageNum, idx) => {
                                        if (pageNum === 'ellipsis') {
                                            return (
                                                <span key={`ellipsis-${idx}`} className="px-2 text-text-tertiary opacity-50">
                                                    ...
                                                </span>
                                            )
                                        }
                                        const pageNumValue = pageNum as number
                                        return (
                                            <button
                                                key={pageNumValue}
                                                onClick={() => setPage(pageNumValue)}
                                                className={`w-8 h-8 rounded-lg text-[11px] font-bold transition-all ${page === pageNumValue
                                                    ? 'bg-primary text-primary-foreground shadow-sm scale-105'
                                                    : 'text-text-secondary hover:bg-primary/10 hover:text-primary border border-transparent'
                                                    }`}
                                            >
                                                {pageNumValue}
                                            </button>
                                        )
                                    })}
                                </div>

                                <Button
                                    variant="secondary"
                                    size="sm"
                                    onClick={() => setPage(prev => Math.min(totalPages, prev + 1))}
                                    disabled={loading || page === totalPages}
                                    className="h-8 px-3 rounded-lg border border-border/50 hover:bg-primary/5 text-[11px] font-bold uppercase tracking-tight"
                                >
                                    Next <ChevronRight className="w-3.5 h-3.5 ml-1" />
                                </Button>
                            </div>

                            {/* Page summary */}
                            <div className="text-[11px] text-text-secondary font-medium uppercase tracking-wider">
                                Showing <span className="text-text-primary font-bold">
                                    {total > 0 ? ((page - 1) * pageSize) + 1 : 0} - {Math.min(page * pageSize, total)}
                                </span> of <span className="text-text-primary font-bold">{total}</span> items
                            </div>
                        </div>
                    )}
                </>
            )}

            {!loading && news.length === 0 && (
                <div className="py-20 text-center">
                    <div className="inline-block p-4 rounded-full bg-text-secondary/5 mb-4">
                        <Radio className="w-8 h-8 text-text-tertiary opacity-20" />
                    </div>
                    <p className="text-text-secondary font-sans text-sm">No news items available yet.</p>
                    <p className="text-[9px] text-text-tertiary mt-1 uppercase tracking-wider">Waiting for real-time updates...</p>
                </div>
            )}
        </div>
    )
}
