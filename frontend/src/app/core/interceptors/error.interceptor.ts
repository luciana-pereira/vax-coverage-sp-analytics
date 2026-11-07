import { HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { TimeoutError, catchError, retry, throwError, timeout, timer } from 'rxjs';

import { API_BASE_URL } from '../config/api-config';

export const API_REQUEST_TIMEOUT_MS = 90_000;
export const API_RETRY_DELAY_MS = 1_000;

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
  const safeDetail =
    typeof detail === 'string' &&
    detail.length <= 200 &&
    !/(traceback|stack trace|exception|File\s+"|[A-Za-z]:[\\/])/i.test(detail)
      ? detail
      : null;
  const messages: Record<number, string> = {
    400: 'Verifique os filtros e os parâmetros informados.',
    401: 'Sua sessão expirou. Entre novamente para continuar.',
    403: 'Você não tem permissão para acessar estes dados.',
    404: 'O recurso solicitado não foi encontrado.',
    409: 'A solicitação conflita com o estado atual dos dados.',
    422: 'Os parâmetros ou dados enviados não são válidos.',
    429: 'Muitas solicitações em pouco tempo. Aguarde e tente novamente.',
  };
  const message =
    error.status >= 500
      ? 'O serviço encontrou um erro. Tente novamente mais tarde.'
      : safeDetail ?? messages[error.status] ?? 'Não foi possível concluir a solicitação.';
  return new ApiError(message, error.status);
}

export const errorInterceptor: HttpInterceptorFn = (req, next) => {
  const baseUrl = inject(API_BASE_URL).replace(/\/+$/, '');
  const isApiRequest = req.url === baseUrl || req.url.startsWith(`${baseUrl}/`);

  return next(req).pipe(
    timeout({ each: API_REQUEST_TIMEOUT_MS }),
    retry({
      count: 1,
      delay: (error: unknown) => {
        const transient =
          error instanceof TimeoutError ||
          (error instanceof HttpErrorResponse && [0, 502, 503, 504].includes(error.status));
        return isApiRequest && req.method === 'GET' && transient
          ? timer(API_RETRY_DELAY_MS)
          : throwError(() => error);
      },
    }),
    catchError((error: unknown) => {
      if (error instanceof TimeoutError) {
        return throwError(() => new ApiError('A API demorou para responder. Tente novamente.', 0));
      }
      return throwError(() => (error instanceof HttpErrorResponse ? toApiError(error) : error));
    }),
  );
};
