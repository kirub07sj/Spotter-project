import type { components } from './schema';

type Schemas = components['schemas'];

export type Plan = Schemas['PlanResponse'];
export type Route = Schemas['Route'];
export type Checkpoint = Schemas['Checkpoint'];
export type RiskSegment = Schemas['RiskSegment'];
export type RiskLevel = Schemas['RiskLevel'];
export type RouteId = Schemas['RouteId'];
export type Place = Schemas['Place'];
export type PlanRequest = Schemas['PlanRequestRequest'];
export type Problem = Schemas['Problem'];
export type ProblemCode = Problem['code'];
export type PlanWarning = Schemas['Warning'];
export type Scenario = Schemas['ScenarioEnum'];
export type HeatmapResponse = Schemas['HeatmapResponse'];
export type HeatmapRequest = Schemas['HeatmapRequestRequest'];
export type Grid = Schemas['Grid'];
