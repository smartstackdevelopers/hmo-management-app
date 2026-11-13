import { hmoreFetch } from '@/lib/hmore/client';

export interface RentObligation {
  rent_record_id: string;
  payment_status: string;
  outstanding_balance: string;
  currency: string;
  due_date: string | null;
}

export function listMyRentObligations(): Promise<RentObligation[]> {
  return hmoreFetch<RentObligation[]>('/rent-payments/obligations', { method: 'GET' });
}

export function createRentCheckout(rentRecordId: string): Promise<Record<string, unknown>> {
  return hmoreFetch<Record<string, unknown>>('/rent-payments/checkout-sessions', {
    method: 'POST',
    body: { rent_record_id: rentRecordId },
  });
}
