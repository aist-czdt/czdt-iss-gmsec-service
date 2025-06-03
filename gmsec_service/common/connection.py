import libgmsec_python3 as lp


class GmsecConnection(object):
    """
    A class to manage a GMSEC connection. Handles setting up, tearing down, and maintaining
    the connection to the GMSEC Bus.

    Attributes:
        config (lp.ConfigFile): The loaded configuration file.
        conn (lp.Connection): The connection instance to GMSEC Bus.
        subscription (lp.SubscriptionEntry): The subscription details.
    """

    SYSTEM = "CZDT"
    SUBSYSTEM = "ISS"
    FACILITY = "JPL"
    COMPONENT = "PRODUCT-INGEST"

    config: lp.Config
    subscription: lp.SubscriptionEntry
    conn: lp.Connection

    def __init__(self, config_fp: str):
        """
        Initializes the connection with the provided parameters.

        Args:
            config_fp (str): The relative path to the configuration file.
            subscription_name (str): The name of the subscritption.
        """
        # Load config from file
        config_file = lp.ConfigFile()
        config_file.load(config_fp)
        self.config = config_file.lookup_config("config")
        self.config_file = config_file

        # Initialize log level
        level = lp.Log.from_string(self.config.get_value("loglevel", "info"))
        lp.Log.set_reporting_level(level)
        lp.log_info(f"Using config file --> {config_fp}")

        # Create connection instance
        self.conn = lp.Connection(self.config)

        self.msg_factory: lp.MessageFactory = self.conn.get_message_factory()

        # Set up standard fields within the MessageFactory associated with the connection object.
        self.set_standard_fields(self.msg_factory)

        # Establish connection to the GMSEC Bus.
        self.conn.connect()

        # Log connection details (API version and library version)
        lp.log_info(lp.Connection.get_api_version())
        lp.log_info("Middleware version = " + self.conn.get_library_version())

        # Enforce message content validation prior to send
        self.config.add_value("gmsec-msg-content-validate-send", "true")

    def teardown(self):
        """
        Tear down the connection, stop the heartbeat generator, and clean up resources.

        This method disconnects from the GMSEC Bus, stops the heartbeat generator,
        and deletes connection and heartbeat generator objects.
        """
        try:
            # Disconnect from the GMSEC Bus, and terminate subscriptions
            self.conn.disconnect()

            # Destroy the Connection
            del self.conn

        except lp.GmsecError as e:
            # Log error if the teardown process fails
            lp.log_error("Exception: " + str(e))

    def set_standard_fields(self, factory):
        """
        Set standard fields in the MessageFactory associated with the connection.

        Args:
            factory (lp.MessageFactory): The message factory instance.
            system (str): The system identifier.
            subsystem (str): The subsystem identifier.
            facility (str): The facility identifier.
            component (str): The component identifier.
        """
        standardFields = self.get_standard_fields()
        factory.set_standard_fields(standardFields)

    def get_standard_fields(self):
        """
        Generate a list of standard fields used in the GMSEC messages.

        Args:
            system (str): The system identifier.
            subsystem (str): The subsystem identifier.
            facility (str): The facility identifier.
            component (str): The component identifier.

        Returns:
            lp.FieldList: A list of standard fields.
        """
        self.field1 = lp.StringField("SYSTEM", self.SYSTEM, True)
        self.field2 = lp.StringField("SUBSYSTEM", self.SUBSYSTEM, True)
        self.field3 = lp.StringField("FACILITY", self.FACILITY, True)
        self.field4 = lp.StringField("COMPONENT", self.COMPONENT, True)

        standardFields = lp.FieldList()

        standardFields.push_back(self.field1)
        standardFields.push_back(self.field2)
        standardFields.push_back(self.field3)
        standardFields.push_back(self.field4)

        return standardFields

    def get_subscription_pattern(self, subscription_name: str) -> str:
        sub_entry: lp.SubscriptionEntry = self.config_file.lookup_subscription_entry(
            subscription_name
        )
        return sub_entry.get_pattern()
