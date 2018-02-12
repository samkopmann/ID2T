import os
import sys
import readline

from ID2TLib.AttackController import AttackController
from ID2TLib.LabelManager import LabelManager
from ID2TLib.PcapFile import PcapFile
from ID2TLib.Statistics import Statistics


class Controller:
    def __init__(self, pcap_file_path: str, do_extra_tests: bool):
        """
        Creates a new Controller, acting as a central coordinator for the whole application.
        :param pcap_file_path:
        """
        # Fields
        self.pcap_src_path = pcap_file_path.strip()
        self.pcap_dest_path = ''
        self.written_pcaps = []
        self.do_extra_tests = do_extra_tests

        # Initialize class instances
        print("Input file: %s" % self.pcap_src_path)
        self.pcap_file = PcapFile(self.pcap_src_path)
        self.label_manager = LabelManager(self.pcap_src_path)
        self.statistics = Statistics(self.pcap_file)
        self.statistics.do_extra_tests = self.do_extra_tests
        self.statisticsDB = self.statistics.get_statistics_database()
        self.attack_controller = AttackController(self.pcap_file, self.statistics, self.label_manager)

    def load_pcap_statistics(self, flag_write_file: bool, flag_recalculate_stats: bool, flag_print_statistics: bool):
        """
        Loads the PCAP statistics either from the database, if the statistics were calculated earlier, or calculates
        the statistics and creates a new database.
        :param flag_write_file: Writes the statistics to a file.
        :param flag_recalculate_stats: Forces the recalculation of statistics.
        :param flag_print_statistics: Prints the statistics on the terminal.
        :return: None
        """
        self.statistics.load_pcap_statistics(flag_write_file, flag_recalculate_stats, flag_print_statistics)

    def process_attacks(self, attacks_config: list):
        """
        Creates the attack based on the attack name and the attack parameters given in the attacks_config. The
        attacks_config is a list of attacks, e.g.
        [['PortscanAttack', 'ip.src="192.168.178.2",'dst.port=80'],['PortscanAttack', 'ip.src="10.10.10.2"]].
        Merges the individual temporary attack pcaps into one single pcap and merges this single pcap with the
        input dataset.
        :param attacks_config: A list of attacks with their attack parameters.
        """
        # load attacks sequentially
        for attack in attacks_config:
            temp_attack_pcap = self.attack_controller.process_attack(attack[0], attack[1:])
            self.written_pcaps.append(temp_attack_pcap)

        # merge attack pcaps to get single attack pcap
        if len(self.written_pcaps) > 1:
            print("\nMerging temporary attack pcaps into single pcap file...", end=" ")
            sys.stdout.flush()  # force python to print text immediately
            for i in range(0, len(self.written_pcaps) - 1):
                attacks_pcap = PcapFile(self.written_pcaps[i])
                attacks_pcap_path = attacks_pcap.merge_attack(self.written_pcaps[i + 1])
                os.remove(self.written_pcaps[i + 1])  # remove merged pcap
                self.written_pcaps[i + 1] = attacks_pcap_path
            print("done.")
        else:
            attacks_pcap_path = self.written_pcaps[0]

        # merge single attack pcap with all attacks into base pcap
        print("Merging base pcap with single attack pcap...", end=" ")
        sys.stdout.flush()  # force python to print text immediately
        self.pcap_dest_path = self.pcap_file.merge_attack(attacks_pcap_path)
        print("done.")

        # delete intermediate PCAP files
        print('Deleting intermediate attack pcap...', end=" ")
        sys.stdout.flush()  # force python to print text immediately
        os.remove(attacks_pcap_path)
        print("done.")

        # write label file with attacks
        self.label_manager.write_label_file(self.pcap_dest_path)

        # print status message
        print('\nOutput files created: \n', self.pcap_dest_path, '\n', self.label_manager.label_file_path)

    def process_db_queries(self, query, print_results=False):
        """
        Processes a statistics database query. This can be a standard SQL query or a named query.
        :param query: The query as a string or multiple queries as a list of strings.
        :param print_results: Must be True if the results should be printed to terminal.
        :return: The query's result
        """
        print("Processing database query/queries...")
        if isinstance(query, list) or isinstance(query, tuple):
            for q in query:
                self.statisticsDB.process_db_query(q, print_results)
        else:
            self.statisticsDB.process_db_query(query, print_results)

    @staticmethod
    def process_help(params):
        if not params:
            print("Query mode allows you to enter SQL-queries as well as named queries.")
            print()
            print("Named queries:")
            print("\tSelectors:")
            print("\t\tmost_used(...)  -> Returns the most occurring element in all elements")
            print("\t\tleast_used(...) -> Returns the least occurring element in all elements")
            print("\t\tavg(...)        -> Returns the average of all elements")
            print("\t\tall(...)        -> Returns all elements")
            print("\tExtractors:")
            print("\t\trandom(...)     -> Returns a random element from a list")
            print("\t\tfirst(...)      -> Returns the first element from a list")
            print("\t\tlast(...)       -> Returns the last element from a list")
            print("\tParameterized selectors:")
            print("\t\tipAddress(...)  -> Returns all IP addresses fulfilling the specified conditions")
            print("\t\tmacAddress(...) -> Returns all MAC addresses fulfilling the specified conditions")
            print()
            print("Additional information is available with 'help [KEYWORD];'")
            print("To get a list of examples, type 'help examples;'")
            print()
            return

        param = params[0].lower()
        if param == "most_used":
            print("most_used can be used as a selector for the following attributes:")
            print("ipAddress | macAddress | portNumber | protocolName | ttlValue | mssValue | winSize | ipClass")
            print()
        elif param == "least_used":
            print("least_used can be used as a selector for the following attributes:")
            print("ipAddress | macAddress | portNumber | protocolName | ttlValue")
            print()
        elif param == "avg":
            print("avg can be used as a selector for the following attributes:")
            print("pktsReceived | pktsSent | kbytesSent | kbytesReceived | ttlValue | mss")
            print()
        elif param == "all":
            print("all can be used as a selector for the following attributes:")
            print("ipAddress | ttlValue | mss | macAddress | portNumber | protocolName")
            print()
        elif param in ["random", "first", "last"]:
            print("No additional info available for this keyword.")
            print()
        elif param == "ipaddress":
            print("ipAddress is a parameterized selector which fetches IP addresses based on (a list of) conditions.")
            print("Conditions are of the following form: PARAMETER OPERATOR VALUE")
            print("The following parameters can be specified:")
            print("pktsReceived | pktsSent | kbytesReceived | kbytesSent | maxPktRate | minPktRate | macAddress\n"
                  "ttlValue | ttlCount | portDirection | portDirection | portNumber | portCount | protocolCount")
            print()
            print("See 'help examples;' for usage examples.")
            print()
        elif param == "macaddress":
            print("macAddress is a parameterized selector which fetches MAC addresses based on (a list of) conditions.")
            print("Conditions are of the following form: PARAMETER OPERATOR VALUE")
            print("The following parameters can be specified:")
            print("ipAddress")
            print()
            print("See 'help examples;' for usage examples.")
            print()
        elif param == "examples":
            print("Get the average amount of sent packets per IP:")
            print("\tavg(pktsSent);")
            print("Get a random IP from all addresses occuring in the pcap:")
            print("\trandom(all(ipAddress));")
            print("Return the MAC address of a specified IP:")
            print("\tmacAddress(ipAddress=192.168.178.2);")
            print("Get the average TTL-value with SQL:")
            print("\tSELECT avg(ttlValue) from ip_ttl;")
            print("Get a random IP address from all addresses that sent and received at least 10 packets:")
            print("\trandom(ipAddress(pktsSent > 10, pktsReceived > 10));")
            print()
        else:
            print("Unknown keyword '" + param + "', try 'help;' to get a list of allowed keywords'")
            print()

    def enter_query_mode(self):
        """
        Enters into the query mode. This is a read-eval-print-loop, where the user can input named queries or SQL
        queries and the results are printed.
        """

        def make_completer(vocabulary):
            def custom_template(text, state):
                results = [x for x in vocabulary if x.startswith(text)] + [None]
                return results[state]
            return custom_template

        readline.parse_and_bind('tab: complete')
        readline.set_completer(make_completer(self.statisticsDB.get_all_named_query_keywords()+self.statisticsDB.get_all_sql_query_keywords()))
        history_file = os.path.join(os.path.expanduser('~'), 'ID2T_data', 'query_history')
        try:
            readline.read_history_file(history_file)
        except IOError:
            pass
        print("Entering into query mode...")
        print("Enter statement ending by ';' and press ENTER to send query. Exit by sending an empty query.")
        print("Type 'help;' for information on possible queries.")
        buffer = ""
        while True:
            line = input("> ")
            if line == "":
                break
            buffer += line
            import sqlite3
            if sqlite3.complete_statement(buffer):
                try:
                    buffer = buffer.strip()
                    if buffer.lower().startswith('help'):
                        buffer = buffer.strip(';')
                        self.process_help(buffer.split(' ')[1:])
                    else:
                        self.statisticsDB.process_db_query(buffer, True)
                except sqlite3.Error as e:
                    print("An error occurred:", e.args[0])
                buffer = ""

        readline.set_history_length(1000)
        readline.write_history_file(history_file)

    def create_statistics_plot(self, params: str):
        """
        Plots the statistics to a file by using the given customization parameters.
        """
        if params is not None and params[0] is not None:
            params_dict = dict([z.split("=") for z in params])
            self.statistics.plot_statistics(format=params_dict['format'])
        else:
            self.statistics.plot_statistics()
