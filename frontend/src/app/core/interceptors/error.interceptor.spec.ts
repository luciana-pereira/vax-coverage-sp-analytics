import { HttpErrorResponse } from '@angular/common/http';

import { toApiError } from './error.interceptor';

describe('toApiError', () => {
  const messages = new Map<number, string>([
    [400, 'Verifique os filtros e os parâmetros informados.'],
    [401, 'Sua sessão expirou. Entre novamente para continuar.'],
    [403, 'Você não tem permissão para acessar estes dados.'],
    [404, 'O recurso solicitado não foi encontrado.'],
    [409, 'A solicitação conflita com o estado atual dos dados.'],
    [422, 'Os parâmetros ou dados enviados não são válidos.'],
    [429, 'Muitas solicitações em pouco tempo. Aguarde e tente novamente.'],
    [500, 'O serviço encontrou um erro. Tente novamente mais tarde.'],
  ]);

  for (const [status, message] of messages) {
    it(`uses a friendly message for HTTP ${status}`, () => {
      const error = new HttpErrorResponse({
        status,
        statusText: 'Error',
        error: { detail: 'Traceback: C:\\internal\\secret.py' },
      });

      expect(toApiError(error).message).toBe(message);
    });
  }

  it('keeps a short not-found detail from the API', () => {
    const error = new HttpErrorResponse({
      status: 404,
      statusText: 'Not Found',
      error: { detail: 'Município sem registros.' },
    });

    expect(toApiError(error).message).toBe('Município sem registros.');
  });
});
