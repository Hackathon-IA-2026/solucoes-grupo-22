import { EModelEndpoint } from 'librechat-data-provider';
import type { EndpointTokenConfig } from '~/types';
import { getModelMaxTokens, getModelMaxOutputTokens } from './tokens';

describe('getModelMaxTokens partial-override fallback', () => {
  const partialOverride: EndpointTokenConfig = {
    'custom-model': { prompt: 1, completion: 2, context: 32000, output: 4096 },
  };

  it('uses the override for a listed model', () => {
    expect(getModelMaxTokens('custom-model', EModelEndpoint.openAI, partialOverride)).toBe(32000);
  });

  it('falls back to the built-in map for a model absent from a partial override', () => {
    const fallback = getModelMaxTokens('gpt-4o', EModelEndpoint.openAI, partialOverride);
    const builtin = getModelMaxTokens('gpt-4o', EModelEndpoint.openAI);
    expect(fallback).toBe(builtin);
    expect(fallback).toBeGreaterThan(100000);
  });
});

describe('Claude 5 family on bedrock and anthropic', () => {
  // The EnergyNexus profiles run `us.anthropic.claude-sonnet-5`/`claude-opus-5`; without an entry in
  // `anthropicModels` these fall back to the generic `claude-` prefix (100k) and history gets pruned.
  it.each([
    ['us.anthropic.claude-sonnet-5', 1000000],
    ['us.anthropic.claude-opus-5', 1000000],
  ])('resolves the 1M context of %s on bedrock', (model, context) => {
    expect(getModelMaxTokens(model, EModelEndpoint.bedrock)).toBe(context);
  });

  it.each([
    ['claude-sonnet-5', 128000],
    ['claude-opus-5', 128000],
  ])('resolves the 128k max output of %s on anthropic', (model, output) => {
    expect(getModelMaxOutputTokens(model, EModelEndpoint.anthropic)).toBe(output);
  });
});

describe('getModelMaxOutputTokens partial-override fallback', () => {
  const partialOverride: EndpointTokenConfig = {
    'custom-model': { prompt: 1, completion: 2, context: 32000, output: 4096 },
  };

  it('falls back to the built-in map for a model absent from a partial override', () => {
    const fallback = getModelMaxOutputTokens('gpt-4o', EModelEndpoint.openAI, partialOverride);
    const builtin = getModelMaxOutputTokens('gpt-4o', EModelEndpoint.openAI);
    expect(fallback).toBe(builtin);
    expect(fallback).toBeGreaterThan(0);
  });
});
