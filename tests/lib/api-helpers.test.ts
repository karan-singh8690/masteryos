import { describe, it, expect } from 'vitest'

import {
  paginationParams,
  toPaginatedResponse,
  ApiError,
  tokenStorage,
} from '@/lib/api-client'

describe('paginationParams', () => {
  it('returns empty for undefined', () => {
    expect(paginationParams(undefined)).toEqual({})
  })

  it('returns empty for empty object', () => {
    expect(paginationParams({})).toEqual({})
  })

  it('converts page', () => {
    expect(paginationParams({ page: 1 })).toEqual({ page: '1' })
  })

  it('converts pageSize', () => {
    expect(paginationParams({ pageSize: 20 })).toEqual({ page_size: '20' })
  })

  it('converts sortBy', () => {
    expect(paginationParams({ sortBy: 'name' })).toEqual({ sort_by: 'name' })
  })

  it('converts sortOrder', () => {
    expect(paginationParams({ sortOrder: 'asc' })).toEqual({ sort_order: 'asc' })
    expect(paginationParams({ sortOrder: 'desc' })).toEqual({ sort_order: 'desc' })
  })

  it('converts all params', () => {
    expect(
      paginationParams({ page: 2, pageSize: 50, sortBy: 'created_at', sortOrder: 'desc' }),
    ).toEqual({
      page: '2',
      page_size: '50',
      sort_by: 'created_at',
      sort_order: 'desc',
    })
  })
})

describe('toPaginatedResponse', () => {
  it('creates response with correct hasNext/hasPrev', () => {
    const result = toPaginatedResponse([1, 2, 3], 100, { page: 1, pageSize: 10 })
    expect(result.hasNext).toBe(true)
    expect(result.hasPrev).toBe(false)
  })

  it('handles middle page', () => {
    const result = toPaginatedResponse([1, 2, 3], 100, { page: 5, pageSize: 10 })
    expect(result.hasNext).toBe(true)
    expect(result.hasPrev).toBe(true)
  })

  it('handles last page', () => {
    const result = toPaginatedResponse([1, 2, 3], 30, { page: 3, pageSize: 10 })
    expect(result.hasNext).toBe(false)
    expect(result.hasPrev).toBe(true)
  })

  it('handles single page', () => {
    const result = toPaginatedResponse([1, 2, 3], 3, { page: 1, pageSize: 10 })
    expect(result.hasNext).toBe(false)
    expect(result.hasPrev).toBe(false)
  })

  it('uses defaults when params not provided', () => {
    const result = toPaginatedResponse([1, 2, 3], 30, {})
    expect(result.page).toBe(1)
    expect(result.pageSize).toBe(20)
  })
})

describe('ApiError', () => {
  it('constructs with all fields', () => {
    const error = new ApiError('msg', 400, 'CODE', { field: ['err'] }, 'corr-id')
    expect(error.message).toBe('msg')
    expect(error.statusCode).toBe(400)
    expect(error.code).toBe('CODE')
    expect(error.fieldErrors).toEqual({ field: ['err'] })
    expect(error.correlationId).toBe('corr-id')
  })

  it('constructs with minimal fields', () => {
    const error = new ApiError('msg', 500, 'ERROR')
    expect(error.fieldErrors).toBeUndefined()
    expect(error.correlationId).toBeUndefined()
  })

  it('is an Error instance', () => {
    const error = new ApiError('msg', 400, 'CODE')
    expect(error).toBeInstanceOf(Error)
    expect(error.name).toBe('ApiError')
  })

  it('fromAxiosError handles network error (no response)', () => {
    const error = ApiError.fromAxiosError({ response: null } as any)
    expect(error.code).toBe('NETWORK_ERROR')
    expect(error.statusCode).toBe(0)
  })

  it('fromAxiosError handles 401', () => {
    const error = ApiError.fromAxiosError({
      response: { status: 401, data: { detail: { code: 'UNAUTHORIZED', message: 'Unauthorized' } } },
      config: { headers: {} },
    } as any)
    expect(error.statusCode).toBe(401)
    expect(error.code).toBe('UNAUTHORIZED')
  })

  it('fromAxiosError handles 403', () => {
    const error = ApiError.fromAxiosError({
      response: { status: 403, data: { detail: { code: 'FORBIDDEN', message: 'Forbidden' } } },
      config: { headers: {} },
    } as any)
    expect(error.statusCode).toBe(403)
    expect(error.code).toBe('FORBIDDEN')
  })

  it('fromAxiosError handles 404', () => {
    const error = ApiError.fromAxiosError({
      response: { status: 404, data: { detail: { code: 'NOT_FOUND', message: 'Not found' } } },
      config: { headers: {} },
    } as any)
    expect(error.statusCode).toBe(404)
  })

  it('fromAxiosError handles 422 with field errors', () => {
    const error = ApiError.fromAxiosError({
      response: {
        status: 422,
        data: {
          detail: {
            code: 'VALIDATION_FAILED',
            message: 'Validation failed',
            fields: { email: ['Already exists'] },
          },
        },
      },
      config: { headers: {} },
    } as any)
    expect(error.statusCode).toBe(422)
    expect(error.fieldErrors).toEqual({ email: ['Already exists'] })
  })

  it('fromAxiosError handles 429', () => {
    const error = ApiError.fromAxiosError({
      response: { status: 429, data: { detail: { code: 'RATE_LIMITED', message: 'Too many requests' } } },
      config: { headers: {} },
    } as any)
    expect(error.statusCode).toBe(429)
    expect(error.code).toBe('RATE_LIMITED')
  })

  it('fromAxiosError handles 500', () => {
    const error = ApiError.fromAxiosError({
      response: { status: 500, data: 'Internal server error' },
      config: { headers: {} },
    } as any)
    expect(error.statusCode).toBe(500)
    expect(error.code).toBe('UNKNOWN_ERROR')
  })

  it('fromAxiosError extracts correlation ID from headers', () => {
    const error = ApiError.fromAxiosError({
      response: { status: 400, data: { detail: { code: 'ERR', message: 'Error' } } },
      config: { headers: { 'X-Correlation-ID': 'test-corr-id' } },
    } as any)
    expect(error.correlationId).toBe('test-corr-id')
  })
})

describe('tokenStorage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('starts with null tokens', () => {
    expect(tokenStorage.getAccessToken()).toBeNull()
    expect(tokenStorage.getRefreshToken()).toBeNull()
  })

  it('stores + retrieves access token', () => {
    tokenStorage.setAccessToken('access-123')
    expect(tokenStorage.getAccessToken()).toBe('access-123')
  })

  it('stores + retrieves refresh token', () => {
    tokenStorage.setRefreshToken('refresh-456')
    expect(tokenStorage.getRefreshToken()).toBe('refresh-456')
  })

  it('clear removes both tokens', () => {
    tokenStorage.setAccessToken('access')
    tokenStorage.setRefreshToken('refresh')
    tokenStorage.clear()
    expect(tokenStorage.getAccessToken()).toBeNull()
    expect(tokenStorage.getRefreshToken()).toBeNull()
  })
})
