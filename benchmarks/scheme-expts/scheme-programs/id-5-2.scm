(let ((imp (λ (a b) (if a b #f))))
  ((λ (f120)
     (let ((m122 (f120 (λ (k) k)))) (let ((m121 (f120 (λ (k) k)))) m122)))
   (λ (z103)
     ((λ (f117)
        (let ((m119 (f117 (λ (k) k)))) (let ((m118 (f117 (λ (k) k)))) m119)))
      (λ (z104)
        ((λ (f114)
           (let ((m116 (f114 (λ (k) k))))
             (let ((m115 (f114 (λ (k) k)))) m116)))
         (λ (z105)
           ((λ (f111)
              (let ((m113 (f111 (λ (k) k))))
                (let ((m112 (f111 (λ (k) k)))) m113)))
            (λ (z106)
              ((λ (f108)
                 (let ((m110 (f108 (λ (k) k))))
                   (let ((m109 (f108 (λ (k) k)))) m110)))
               (λ (z107) (z103 (z104 (z105 (z106 (z107 1))))))))))))))))
