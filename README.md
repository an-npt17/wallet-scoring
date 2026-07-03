# wallet-scoring

A Elite wallet score với side-aware skill decomposition là hướng có giá trị thương mại trực tiếp nhất. Điểm
khác biệt quan trọng là đừng chấm điểm ví bằng một con số PnL duy nhất; nên tách ít nhất thành buy skill,
sell skill, timing skill, sizing skill, và crowd-adjusted skill theo asset/regime. Lý do là ngay cả với institutional
investors, NBER cho thấy buying có thể có skill rõ ràng trong khi selling lại underperform nặng, nên một
score tốt phải “side-aware”, không nên trộn hai phía vào một chỉ số đơn. Đồng thời, copy-trading chỉ tạo giá
trị khi bạn nhận diện đúng leaders; nghiên cứu gần đây trên Polymarket cho thấy copy trades outperform
non-copy trades của chính follower trong cùng market, nhưng nghiên cứu về crypto copy-trading platforms
cũng cho thấy ranking/UI của nền tảng có thể ảnh hưởng mạnh tới quyết định copy và thậm chí dễ bị game.
Vì vậy, paper hay sản phẩm tốt ở đây không phải là “top wallets by ROI”, mà là posterior skill score kèm
confidence interval và expected future value if copied with delay.
