"""
BOLT Beamline Application Registry.

Provides registry configuration for the BOLT imaging beamline application,
including capability and context class registrations for the Alpha Berkeley
Agent Framework. This registry enables motor control, detector imaging, and
photogrammetry scan execution for the BOLT beamline system.

The registry follows the framework's convention-based discovery pattern,
registering BOLT beamline capabilities and their associated context classes
for automatic loading and integration with the LangGraph execution system.

This module serves as the integration point between the BOLT beamline components
and the framework's registry system, enabling automatic discovery of capabilities
and context classes without manual configuration.
"""

from framework.registry import (
    CapabilityRegistration, 
    ContextClassRegistration, 
    RegistryConfig,
    RegistryConfigProvider
)

class BoltRegistryProvider(RegistryConfigProvider):
    
    def get_registry_config(self) -> RegistryConfig:
        return RegistryConfig(
            capabilities=[
                CapabilityRegistration(
                    name="generate_bluesky_exec",
                    module_path="applications.bolt.capabilities.generate_bluesky_exec",
                    class_name="GenerateBlueskyExecCapability", 
                    description="Generate a Bluesky execution plan",
                    provides=["BLUESKY_PLAN"],
                    requires=[]
                ),
            ],
            
            context_classes=[
                ContextClassRegistration(
                    context_type="BLUESKY_PLAN",
                    module_path="applications.bolt.context_classes", 
                    class_name="CurrentGenerateBlueskyExecContext"
                ),
            ]
        )