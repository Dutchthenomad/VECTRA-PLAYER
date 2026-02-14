# Pipeline D: Training Data Implementation

Complete the training data pipeline to transform Parquet event data into RL-ready training batches. This enables machine learning models to train on historical trading data with proper observation/action/reward structures.

## Rationale
Core blocker for RL model training - users cannot train bots without a working data pipeline. This directly addresses the pain point of 'Difficulty collecting high-quality training data for RL models'.

## User Stories
- As an ML researcher, I want to load captured trading sessions as training data so that I can train RL models on historical patterns
- As a data scientist, I want consistent feature extraction so that model training is reproducible

## Acceptance Criteria
- [ ] Observation schema extracts 36 features from Parquet events
- [ ] Transitions (obs, action, reward, next_obs, done) are correctly generated
- [ ] Batch loader provides training-ready data to RL frameworks
- [ ] Integration tests verify pipeline with real captured data
- [ ] Documentation explains feature engineering choices
