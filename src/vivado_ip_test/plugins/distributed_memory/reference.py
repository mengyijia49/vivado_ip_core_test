class DistributedMemoryModel:
    def __init__(self, parameters):
        self.p = parameters
        self.memory = [parameters["initial_value"]] * parameters["depth"]

    def step(self, inputs):
        if inputs["we"]:
            self.memory[inputs["a"]] = inputs["d"]
        result = {"spo": self.memory[inputs["a"]]}
        if self.p["memory_type"] == "dual_port_ram":
            result["dpo"] = self.memory[inputs["dpra"]]
        return result
