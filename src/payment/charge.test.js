const test = require('node:test');
const assert = require('node:assert/strict');

const otel = require('@opentelemetry/api');
const { OpenFeature } = require('@openfeature/server-sdk');
const logger = require('./logger');

test('charges a valid Visa card', async (t) => {
  const span = {
    setAttributes: t.mock.fn(),
    setAttribute: t.mock.fn(),
    end: t.mock.fn(),
  };

  const counter = {
    add: t.mock.fn(),
  };

  t.mock.method(otel.trace, 'getTracer', () => ({
    startSpan: () => span,
  }));

  t.mock.method(otel.metrics, 'getMeter', () => ({
    createCounter: () => counter,
  }));

  t.mock.method(OpenFeature, 'getClient', () => ({
    getNumberValue: async () => 0,
  }));

  t.mock.method(logger, 'info', () => {});

  delete require.cache[require.resolve('./charge')];
  const { charge } = require('./charge');

  const result = await charge({
    creditCard: {
      creditCardNumber: '4111' + '1'.repeat(12),
      creditCardExpirationMonth: 12,
      creditCardExpirationYear: new Date().getFullYear() + 2,
    },
    amount: {
      units: 10,
      nanos: 0,
      currencyCode: 'USD',
    },
  });

  assert.equal(typeof result.transactionId, 'string');
  assert.ok(result.transactionId.length > 0);
  assert.equal(counter.add.mock.callCount(), 1);
  assert.equal(span.end.mock.callCount(), 1);
});

test('charges a valid Mastercard', async (t) => {
  const span = {
    setAttributes: t.mock.fn(),
    setAttribute: t.mock.fn(),
    end: t.mock.fn(),
  };

  const counter = {
    add: t.mock.fn(),
  };

  t.mock.method(otel.trace, 'getTracer', () => ({
    startSpan: () => span,
  }));

  t.mock.method(otel.metrics, 'getMeter', () => ({
    createCounter: () => counter,
  }));

  t.mock.method(OpenFeature, 'getClient', () => ({
    getNumberValue: async () => 0,
  }));

  t.mock.method(logger, 'info', () => {});

  delete require.cache[require.resolve('./charge')];
  const { charge } = require('./charge');

  const result = await charge({
    creditCard: {
      creditCardNumber: '5555' + '5555' + '5555' + '4444',
      creditCardExpirationMonth: 12,
      creditCardExpirationYear: new Date().getFullYear() + 2,
    },
    amount: {
      units: 10,
      nanos: 0,
      currencyCode: 'USD',
    },
  });

  assert.equal(typeof result.transactionId, 'string');
  assert.ok(result.transactionId.length > 0);
  assert.equal(counter.add.mock.callCount(), 1);
  assert.equal(span.end.mock.callCount(), 1);
});

test('rejects an invalid card number and ends the span', async (t) => {
  const span = {
    setAttributes: t.mock.fn(),
    setAttribute: t.mock.fn(),
    end: t.mock.fn(),
  };

  t.mock.method(otel.trace, 'getTracer', () => ({
    startSpan: () => span,
  }));

  t.mock.method(otel.metrics, 'getMeter', () => ({
    createCounter: () => ({ add: t.mock.fn() }),
  }));

  t.mock.method(OpenFeature, 'getClient', () => ({
    getNumberValue: async () => 0,
  }));

  t.mock.method(logger, 'info', () => {});

  delete require.cache[require.resolve('./charge')];
  const { charge } = require('./charge');

  await assert.rejects(
    charge({
      creditCard: {
        creditCardNumber: '4111' + '1'.repeat(11) + '2',
        creditCardExpirationMonth: 12,
        creditCardExpirationYear: new Date().getFullYear() + 2,
      },
      amount: {
        units: 10,
        nanos: 0,
        currencyCode: 'USD',
      },
    }),
    /Credit card info is invalid/
  );

  assert.equal(span.end.mock.callCount(), 1);
});

test('rejects an unsupported card type and ends the span', async (t) => {
  const span = {
    setAttributes: t.mock.fn(),
    setAttribute: t.mock.fn(),
    end: t.mock.fn(),
  };

  t.mock.method(otel.trace, 'getTracer', () => ({
    startSpan: () => span,
  }));

  t.mock.method(otel.metrics, 'getMeter', () => ({
    createCounter: () => ({ add: t.mock.fn() }),
  }));

  t.mock.method(OpenFeature, 'getClient', () => ({
    getNumberValue: async () => 0,
  }));

  t.mock.method(logger, 'info', () => {});

  delete require.cache[require.resolve('./charge')];
  const { charge } = require('./charge');

  await assert.rejects(
    charge({
      creditCard: {
        creditCardNumber: '3782' + '8224' + '6310' + '005',
        creditCardExpirationMonth: 12,
        creditCardExpirationYear: new Date().getFullYear() + 2,
      },
      amount: {
        units: 10,
        nanos: 0,
        currencyCode: 'USD',
      },
    }),
    /Only VISA or MasterCard is accepted/
  );

  assert.equal(span.end.mock.callCount(), 1);
});

test('rejects an expired card and ends the span', async (t) => {
  const span = {
    setAttributes: t.mock.fn(),
    setAttribute: t.mock.fn(),
    end: t.mock.fn(),
  };

  t.mock.method(otel.trace, 'getTracer', () => ({
    startSpan: () => span,
  }));

  t.mock.method(otel.metrics, 'getMeter', () => ({
    createCounter: () => ({ add: t.mock.fn() }),
  }));

  t.mock.method(OpenFeature, 'getClient', () => ({
    getNumberValue: async () => 0,
  }));

  t.mock.method(logger, 'info', () => {});

  delete require.cache[require.resolve('./charge')];
  const { charge } = require('./charge');

  await assert.rejects(
    charge({
      creditCard: {
        creditCardNumber: '4111' + '1'.repeat(12),
        creditCardExpirationMonth: 12,
        creditCardExpirationYear: new Date().getFullYear() - 1,
      },
      amount: {
        units: 10,
        nanos: 0,
        currencyCode: 'USD',
      },
    }),
    /expired on/
  );

  assert.equal(span.end.mock.callCount(), 1);
});

test('fails deterministically when paymentFailure feature flag is triggered', async (t) => {
  const span = {
    setAttributes: t.mock.fn(),
    setAttribute: t.mock.fn(),
    end: t.mock.fn(),
  };

  t.mock.method(otel.trace, 'getTracer', () => ({
    startSpan: () => span,
  }));

  t.mock.method(otel.metrics, 'getMeter', () => ({
    createCounter: () => ({ add: t.mock.fn() }),
  }));

  t.mock.method(OpenFeature, 'getClient', () => ({
    getNumberValue: async () => 1,
  }));

  t.mock.method(Math, 'random', () => 0);
  t.mock.method(logger, 'info', () => {});

  delete require.cache[require.resolve('./charge')];
  const { charge } = require('./charge');

  await assert.rejects(
    charge({}),
    /Payment request failed\. Invalid token/
  );

  assert.equal(span.end.mock.callCount(), 1);
});
