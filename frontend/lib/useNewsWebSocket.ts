'use client'

import { useEffect, useState, useRef, useCallback } from 'react'
import Cookies from 'js-cookie'

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

const getWebSocketUrl = (): string => {
    const url = API_URL.replace(/^http/, 'ws')
    const token = Cookies.get('auth_token')
    const wsPath = `${url}/api/v1/ws`
    return token ? `${wsPath}?token=${token}` : wsPath
}

export interface NewsItem {
    news_id: number
    received_date?: string
    headline?: string
    summary?: string
    company_name?: string
    ticker?: string
    exchange?: string
    country_code?: string
    sentiment?: string
    url?: string
    impact_score?: number
    created_at?: string
}

interface UseNewsWebSocketReturn {
    isConnected: boolean
    error: Error | null
}

export function useNewsWebSocket(
    onNewNews?: (news: NewsItem) => void
): UseNewsWebSocketReturn {
    const [isConnected, setIsConnected] = useState(false)
    const [error, setError] = useState<Error | null>(null)
    const wsRef = useRef<WebSocket | null>(null)
    const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null)
    const reconnectAttemptsRef = useRef(0)
    const isConnectingRef = useRef(false)
    const maxReconnectAttempts = 10
    const reconnectDelay = 3000

    const onNewNewsRef = useRef(onNewNews)
    onNewNewsRef.current = onNewNews

    const connect = useCallback(() => {
        if (isConnectingRef.current) return

        const token = Cookies.get('auth_token')
        if (!token || wsRef.current?.readyState === WebSocket.OPEN) return

        isConnectingRef.current = true

        try {
            const wsUrl = getWebSocketUrl()
            const ws = new WebSocket(wsUrl)

            ws.onopen = () => {
                isConnectingRef.current = false
                setIsConnected(true)
                setError(null)
                reconnectAttemptsRef.current = 0
                console.log('[News WebSocket] Connected')
            }

            ws.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data)
                    if (data.type === 'news_update' || data.event === 'new_news') {
                        const news = data.data || data
                        if (news && news.news_id) {
                            onNewNewsRef.current?.(news)
                        }
                    }
                } catch (err) {
                    console.warn('[News WebSocket] Failed to parse message:', err)
                }
            }

            ws.onerror = (err) => {
                console.warn('[News WebSocket] Error:', err)
                isConnectingRef.current = false
                setError(new Error('WebSocket connection error'))
            }

            ws.onclose = () => {
                isConnectingRef.current = false
                setIsConnected(false)
                wsRef.current = null

                if (reconnectAttemptsRef.current < maxReconnectAttempts) {
                    reconnectAttemptsRef.current++
                    reconnectTimeoutRef.current = setTimeout(() => {
                        connect()
                    }, reconnectDelay)
                } else {
                    setError(new Error('WebSocket connection failed after multiple attempts'))
                }
            }

            wsRef.current = ws
        } catch (err) {
            console.warn('[News WebSocket] Failed to create connection:', err)
            isConnectingRef.current = false
            setError(err instanceof Error ? err : new Error('Failed to create WebSocket'))
        }
    }, [])

    const disconnect = useCallback(() => {
        if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current)
            reconnectTimeoutRef.current = null
        }
        if (wsRef.current) {
            wsRef.current.close()
            wsRef.current = null
        }
        isConnectingRef.current = false
        setIsConnected(false)
    }, [])

    useEffect(() => {
        const token = Cookies.get('auth_token')
        if (token) connect()
        return () => disconnect()
    }, [connect, disconnect])

    return { isConnected, error }
}
