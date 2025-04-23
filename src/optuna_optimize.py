import argparse
import optuna
import pandas as pd
from backtest import algo, dynamic_algo

def objective(trial: optuna.Trial, data: pd.DataFrame) -> float:
    """Optimizes final in-sample asset value."""
    # suggest parameters
    # Momentum
    mp = trial.suggest_int('momentum_fast_ema', 1, 25)
    ms = trial.suggest_int('momentum_slow_ema', 1, 40)
    mm = trial.suggest_int('momentum_signal_ema', 1, 20)
    rw = trial.suggest_int('momentum_rsi_window', 1, 50)
    rt = trial.suggest_int('momentum_rsi_threshold', 1, 30)
    aw = trial.suggest_int('momentum_atr_window', 1, 20)
    at = trial.suggest_float('momentum_atr_multiplier', 0.5, 10.0)
    rp = trial.suggest_int('reversion_fast_ema', 1, 25)
    rs = trial.suggest_int('reversion_slow_ema', 1, 40)
    rm = trial.suggest_int('reversion_signal_ema', 1, 20)
    rw2= trial.suggest_int('reversion_rsi_window', 1, 50)
    aw2= trial.suggest_int('reversion_atr_window', 1, 20)
    at2= trial.suggest_float('reversion_atr_multiplier', 0.5, 10.0)

    df = algo(
        data, mp, ms, mm,
        rw, rt, aw, at,
        rp, rs, rm,
        rw2, aw2, at2
    )
    return df['Asset'].iloc[-1]

def dynamic_objective(trial, data: pd.DataFrame) -> float:
    m_fe = trial.suggest_int('momentum_fast_ema', 5, 20)
    m_se = trial.suggest_int('momentum_slow_ema', 21, 50)
    m_sig= trial.suggest_int('momentum_signal_ema', 5, 15)
    m_rsi= trial.suggest_int('momentum_rsi_window', 5, 14)
    m_thr= trial.suggest_int('momentum_rsi_threshold', 20, 50)
    m_atw= trial.suggest_int('momentum_atr_window', 5, 20)
    r_fe = trial.suggest_int('reversion_fast_ema', 5, 20)
    r_se = trial.suggest_int('reversion_slow_ema', 20, 60)
    r_sig= trial.suggest_int('reversion_signal_ema', 5, 20)
    r_rsi= trial.suggest_int('reversion_rsi_window', 5, 20)
    r_atw= trial.suggest_int('reversion_atr_window', 5, 20)
    df = dynamic_algo(
        data, m_fe, m_se, m_sig, m_rsi, m_thr, m_atw,
        r_fe, r_se, r_sig, r_rsi, r_atw
    )
    return df['Asset'].iloc[-1]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Optimize a trading strategy using historical data.")
    parser.add_argument('--data', type=str, default='in_sample.csv', help='Path to the CSV file containing OHLC data.')
    parser.add_argument(
        '--algo', type=str, choices=['static', 'dynamic'], required=True, help='Type of algorithm to run: "static" or "dynamic".'
    )

    args = parser.parse_args()

    # Load data
    data = pd.read_csv(args.data, index_col=0, parse_dates=True)

    if args.algo == 'static':
        study = optuna.create_study(direction='maximize', study_name="opt_VN30F1M")
        study.optimize(lambda t: objective(t, data), n_trials=100000, timeout=600)
    elif args.algo == 'dynamic':
        study = optuna.create_study(direction='maximize', study_name="opt_VN30F1M_dynamic")
        study.optimize(lambda t: dynamic_objective(t, data), n_trials=100000, timeout=600)

    print("Best in-sample final value:", study.best_value)
    print("Best hyperparameters:", study.best_params)