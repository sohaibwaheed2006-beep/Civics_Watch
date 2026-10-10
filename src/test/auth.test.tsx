import { describe, it, expect } from 'vitest';
import { loginSchema, registerSchema } from '@/schemas/auth-schema';
import { createReportSchema, reportCategories } from '@/schemas/report-schema';

describe('Auth Schemas Validation', () => {
  it('validates login form constraints', () => {
    const invalidEmail = loginSchema.safeParse({
      email: 'not-an-email',
      password: '123',
    });
    expect(invalidEmail.success).toBe(false);

    const validLogin = loginSchema.safeParse({
      email: 'citizen@example.com',
      password: 'password123',
    });
    expect(validLogin.success).toBe(true);
  });

  it('validates citizen registration form constraints', () => {
    const mismatchedPasswords = registerSchema.safeParse({
      fullName: 'Sarah Jenkins',
      email: 'sarah@example.com',
      password: 'password123',
      confirmPassword: 'differentpassword',
      agreeToTerms: true,
    });
    expect(mismatchedPasswords.success).toBe(false);

    const validRegister = registerSchema.safeParse({
      fullName: 'Sarah Jenkins',
      email: 'sarah@example.com',
      password: 'password123',
      confirmPassword: 'password123',
      agreeToTerms: true,
    });
    expect(validRegister.success).toBe(true);
  });
});

describe('Report Schemas Validation', () => {
  it('enforces required report fields, title length and coordinates', () => {
    const invalidReport = createReportSchema.safeParse({
      title: 'Pothole', // Too short (min 5)
      description: 'Short', // Too short (min 15)
      category: 'road_damage',
      latitude: undefined,
      longitude: undefined,
    });
    expect(invalidReport.success).toBe(false);

    const validReport = createReportSchema.safeParse({
      title: 'Severe pothole on 5th Ave',
      description: 'A deep pothole has punctured vehicle tires near the crosswalk.',
      category: 'road_damage',
      latitude: 40.7484,
      longitude: -73.9857,
      address: '350 5th Ave, New York, NY',
    });
    expect(validReport.success).toBe(true);
  });

  it('contains all 7 canonical categories', () => {
    expect(reportCategories).toContain('road_damage');
    expect(reportCategories).toContain('streetlight');
    expect(reportCategories).toContain('garbage_waste');
    expect(reportCategories).toContain('water_leak');
    expect(reportCategories).toContain('drainage');
    expect(reportCategories).toContain('public_property');
    expect(reportCategories).toContain('other');
  });
});
