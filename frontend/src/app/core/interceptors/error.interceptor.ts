import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { catchError, throwError } from 'rxjs';

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export function toApiError(error: HttpErrorResponse): ApiError {
  if (error.status === 0) {
    return new ApiError('Não foi possível conectar à API. Verifique se o backend está em execução.', 0);
  }
  const detail = (error.error as { detail?: unknown } | null)?.detail;
  const message = typeof detail === 'string' ? detail : `Falha na requisição (HTTP ${error.status}).`;
  return new ApiError(message, error.status);
}

export const errorInterceptor: HttpInterceptorFn = (req, next) =>
  next(req).pipe(
    catchError((error: unknown) =>
      throwError(() => (error instanceof HttpErrorResponse ? toApiError(error) : error)),
    ),
  );
