import { render, screen, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import Claims from './Claims';
import { AuthProvider } from '../context/AuthContext';
import * as AuthContextModule from '../context/AuthContext';
import * as UseApiModule from '../hooks/useApi';

// Mock useApi
const mockGet = vi.fn();
const mockPost = vi.fn();
const mockPatch = vi.fn();

vi.mock('../hooks/useApi', () => ({
  useApi: () => ({
    get: mockGet,
    post: mockPost,
    patch: mockPatch
  })
}));

describe('Claims Page Component Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test('never renders fraud_reason even if API includes it', async () => {
    // Mock user as customer
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: { id: 1, username: 'test', email: 'test@t.com', role: 'customer' },
      tokens: { access: 'a', refresh: 'r' },
      login: vi.fn(),
      logout: vi.fn(),
    });

    // Mock API response with a malformed claim containing fraud_reason
    mockGet.mockImplementation((url) => {
      if (url === '/claims/') {
        return Promise.resolve({
          data: {
            results: [{
              id: 99,
              policy_number: 'POL-001',
              claim_amount: '1000.00',
              description: 'Test claim',
              date_filed: '2023-01-01',
              status: 'pending',
              fraud_flag: true,
              fraud_reason: 'SECRET_FRAUD_RULE_TRIGGERED' // Should NOT be rendered
            }]
          }
        });
      }
      return Promise.resolve({ data: { results: [] } });
    });

    render(<Claims />);
    
    // Wait for the claim to load
    await waitFor(() => {
      expect(screen.getByText('Test claim')).toBeInTheDocument();
    });

    // Verify the secret reason is nowhere in the DOM
    expect(screen.queryByText('SECRET_FRAUD_RULE_TRIGGERED')).not.toBeInTheDocument();
  });

  test('policy dropdown only includes active policies', async () => {
    vi.spyOn(AuthContextModule, 'useAuth').mockReturnValue({
      user: { id: 1, username: 'test', email: 'test@t.com', role: 'customer' },
      tokens: { access: 'a', refresh: 'r' },
      login: vi.fn(),
      logout: vi.fn(),
    });

    mockGet.mockImplementation((url) => {
      if (url === '/policies/?status=active') {
        return Promise.resolve({
          data: {
            results: [
              { id: 1, policy_number: 'POL-ACTIVE', status: 'active', coverage_amount: '5000' }
            ]
          }
        });
      }
      return Promise.resolve({ data: { results: [] } });
    });

    render(<Claims />);

    // Click "File New Claim"
    const newClaimBtn = await screen.findByText(/File New Claim/i);
    newClaimBtn.click();

    // The dropdown should be rendered and populated with active policy
    await waitFor(() => {
      const option = screen.getByText(/POL-ACTIVE/i);
      expect(option).toBeInTheDocument();
    });
  });
});
