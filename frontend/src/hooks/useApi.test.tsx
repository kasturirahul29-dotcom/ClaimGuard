import { renderHook, waitFor } from '@testing-library/react';
import axios from 'axios';
import MockAdapter from 'axios-mock-adapter';
import { useApi } from './useApi';
import { vi } from 'vitest';
import * as AuthContextModule from '../context/AuthContext';

describe('useApi Integration Test', () => {
  let mockAxios: MockAdapter;

  beforeEach(() => {
    // We need to mock the internal axios instance created inside useApi
    mockAxios = new MockAdapter(axios);
    vi.clearAllMocks();
  });

  afterEach(() => {
    mockAxios.restore();
  });

  test('expired refresh token triggers logout', async () => {
    const mockLogout = vi.fn();
    const mockLogin = vi.fn();
    
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: { id: 1, username: 'test', email: 'test@test.com', role: 'customer' },
      tokens: { access: 'expired_access', refresh: 'expired_refresh' },
      login: mockLogin,
      logout: mockLogout
    });

    const { result } = renderHook(() => useApi());
    const api = result.current;

    // We can't easily intercept the exact `axios.create` instance with axios-mock-adapter globally,
    // so let's mock global axios as fallback, but wait, `useApi` creates its own instance.
    // Actually, `axios-mock-adapter` patches `axios.create` if done right.
    // Let's just mock the HTTP response for any instance by patching XMLHTTPRequest or using mock adapter on the created instance.
    
    // An easier approach for this specific test structure is to mock the POST to /auth/refresh/
    // Since useApi imports axios and calls axios.post directly for the refresh!
    mockAxios.onPost('http://localhost:8000/api/v1/auth/refresh/').reply(401, {
      detail: 'Token is invalid or expired'
    });
    
    // We also need to mock the initial 401 response from the api instance
    const instanceMock = new MockAdapter(api);
    instanceMock.onGet('/some-endpoint').reply(401, {
      detail: 'Given token not valid for any token type'
    });

    try {
      await api.get('/some-endpoint');
    } catch (e) {
      // Expected to throw because the refresh also failed
    }

    await waitFor(() => {
      // The logout function from context should have been called
      expect(mockLogout).toHaveBeenCalledTimes(1);
    });
  });
});
