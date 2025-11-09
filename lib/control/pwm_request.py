class PWMRequest:
    def __init__(self, requester, target_value, start_value=None):
        self.requester = requester
        self.target_value = target_value
        self.start_value = start_value

    
    def get_max_target(requests):
        max_start, max_target = PWMRequest.get_max(requests)
        if max_target is not None:
            return max_target.target_value
        return None


    def get_max_start(requests):
        max_start, max_target = PWMRequest.get_max(requests)
        if max_start is not None:
            return max_target.start_value
        return None


    def get_max_value(max_start, max_target, default):
        return max([
            x for x in [
                max_start.start_value, 
                max_start.target_value, 
                max_target.start_value, 
                max_target.target_value
            ] if x is not None ],
            default=default
        )


    def get_max(requests):
        '''
        Get the maximum requests for the starting condition as well as the
        maximum target request. Both may be None in the case that we don't
        have a anything available. 
        '''
        req_start = None
        req_target = None
        for request in requests:
            if request.start_value is not None:
                if req_start is None or request.start_value > req_start.start_value:
                    req_start = request
            if req_target is None or request.target_value > req_target.target_value:
                req_target = request
        return req_start, req_target


    def __str__(self):
        return '{}({})'.format(
            self.__class__.__name__,
            'start_value={}, target_value={}'.format(str(self.start_value), str(self.target_value))
        )