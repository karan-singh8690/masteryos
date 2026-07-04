import { describe, it, expect, vi, beforeEach } from 'vitest'
import axios from 'axios'

// Mock axios
vi.mock('axios', async () => {
  const actual = await vi.importActual('axios')
  return {
    ...actual,
    default: {
      ...actual.default,
      create: vi.fn(() => ({
        interceptors: {
          request: { use: vi.fn() },
          response: { use: vi.fn() },
        },
        get: vi.fn(),
        post: vi.fn(),
        patch: vi.fn(),
        put: vi.fn(),
        delete: vi.fn(),
      })),
      post: vi.fn(),
    },
  }
})

import { ApiError, paginationParams, toPaginatedResponse } from '@/lib/api-client'

describe('ApiError', () => {
  it('creates error with message + status + code', () => {
    const error = new ApiError('Test error', 400, 'TEST_ERROR')
    expect(error.message).toBe('Test error')
    expect(error.statusCode).toBe(400)
    expect(error.code).toBe('TEST_ERROR')
    expect(error.name).toBe('ApiError')
  })

  it('creates error with field errors', () => {
    const error = new ApiError('Validation failed', 422, 'VALIDATION_FAILED', {
      email: ['Already exists'],
    })
    expect(error.fieldErrors).toEqual({ email: ['Already exists'] })
  })

  it('fromAxiosError handles network error', () => {
    const axiosError = {
      response: null,
      message: 'Network Error',
    } as any
    const error = ApiError.fromAxiosError(axiosError)
    expect(error.statusCode).toBe(0)
    expect(error.code).toBe('NETWORK_ERROR')
  })

  it('fromAxiosError parses backend error', () => {
    const axiosError = {
      response: {
        status: 401,
        data: {
          detail: {
            code: 'INVALID_CREDENTIALS',
            message: 'Invalid email or password',
          },
        },
      },
      config: { headers: {} },
    } as any
    const error = ApiError.fromAxiosError(axiosError)
    expect(error.statusCode).toBe(401)
    expect(error.code).toBe('INVALID_CREDENTIALS')
    expect(error.message).toBe('Invalid email or password')
  })

  it('fromAxiosError handles unknown error format', () => {
    const axiosError = {
      response: {
        status: 500,
        data: 'Internal server error',
      },
      config: { headers: {} },
    } as any
    const error = ApiError.fromAxiosError(axiosError)
    expect(error.statusCode).toBe(500)
    expect(error.code).toBe('UNKNOWN_ERROR')
  })
})

describe('paginationParams', () => {
  it('returns empty object for no params', () => {
    expect(paginationParams()).toEqual({})
  })

  it('converts page + pageSize', () => {
    expect(paginationParams({ page: 1, pageSize: 20 })).toEqual({
      page: '1',
      page_size: '20',
    })
  })

  it('converts sort params', () => {
    expect(
      paginationParams({ sortBy: 'created_at', sortOrder: 'desc' }),
    ).toEqual({
      sort_by: 'created_at',
      sort_order: 'desc',
    })
  })
})

describe('toPaginatedResponse', () => {
  it('creates paginated response', () => {
    const result = toPaginatedResponse([1, 2, 3], 50, { page: 1, pageSize: 10 })
    expect(result.items).toEqual([1, 2, 3])
    expect(result.total).toBe(50)
    expect(result.page).toBe(1)
    expect(result.pageSize).toBe(10)
    expect(result.hasNext).toBe(true)
    expect(result.hasPrev).toBe(false)
  })

  it('handles last page', () => {
    const result = toPaginatedResponse([1, 2, 3], 30, { page: 3, pageSize: 10 })
    expect(result.hasNext).toBe(false)
    expect(result.hasPrev).toBe(true)
  })
})
