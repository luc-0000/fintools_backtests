from db.mysql.db_schemas import Simulator, Rule
from end_points.get_simulator.simulator_schema import SimulatorSchema


def get_sim_result(session, sim_id):
    rows = session.query(Simulator).filter(Simulator.id == sim_id).all()
    sims_schema = SimulatorSchema(many=True,exclude=['earning_info'])
    data = sims_schema.dump(rows)
    return data

def get_sims_for_type(session, rule_type):
    all_sims = session.query(Simulator.id).join(Rule, Simulator.rule_id == Rule.id) \
        .filter(Rule.type == rule_type).all()
    all_sims = [x for (x,) in all_sims]
    return all_sims


